package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

var (
	k8sClient     *kubernetes.Clientset
	dynamicClient dynamic.Interface
	namespace     string
)

func main() {
	// Initialize Kubernetes clients
	if err := initK8sClients(); err != nil {
		log.Fatalf("Failed to initialize Kubernetes clients: %v", err)
	}

	// Get namespace from environment or use default
	namespace = os.Getenv("NAMESPACE")
	if namespace == "" {
		namespace = "default"
	}

	log.Printf("Research Session Operator starting in namespace: %s", namespace)

	// Start watching ResearchSession resources
	go watchResearchSessions()

	// Keep the operator running
	select {}
}

func initK8sClients() error {
	var config *rest.Config
	var err error

	// Try in-cluster config first
	if config, err = rest.InClusterConfig(); err != nil {
		// If in-cluster config fails, try kubeconfig
		kubeconfig := os.Getenv("KUBECONFIG")
		if kubeconfig == "" {
			kubeconfig = fmt.Sprintf("%s/.kube/config", os.Getenv("HOME"))
		}

		if config, err = clientcmd.BuildConfigFromFlags("", kubeconfig); err != nil {
			return fmt.Errorf("failed to create Kubernetes config: %v", err)
		}
	}

	// Create standard Kubernetes client
	k8sClient, err = kubernetes.NewForConfig(config)
	if err != nil {
		return fmt.Errorf("failed to create Kubernetes client: %v", err)
	}

	// Create dynamic client for custom resources
	dynamicClient, err = dynamic.NewForConfig(config)
	if err != nil {
		return fmt.Errorf("failed to create dynamic client: %v", err)
	}

	return nil
}

func getResearchSessionResource() schema.GroupVersionResource {
	return schema.GroupVersionResource{
		Group:    "research.example.com",
		Version:  "v1",
		Resource: "researchsessions",
	}
}

func watchResearchSessions() {
	gvr := getResearchSessionResource()

	for {
		watcher, err := dynamicClient.Resource(gvr).Namespace(namespace).Watch(context.TODO(), v1.ListOptions{})
		if err != nil {
			log.Printf("Failed to create watcher: %v", err)
			time.Sleep(5 * time.Second)
			continue
		}

		log.Println("Watching for ResearchSession events...")

		for event := range watcher.ResultChan() {
			switch event.Type {
			case watch.Added, watch.Modified:
				obj := event.Object.(*unstructured.Unstructured)
				if err := handleResearchSessionEvent(obj); err != nil {
					log.Printf("Error handling ResearchSession event: %v", err)
				}
			case watch.Deleted:
				obj := event.Object.(*unstructured.Unstructured)
				log.Printf("ResearchSession %s deleted", obj.GetName())
			}
		}

		log.Println("Watch channel closed, restarting...")
		watcher.Stop()
		time.Sleep(2 * time.Second)
	}
}

func handleResearchSessionEvent(obj *unstructured.Unstructured) error {
	name := obj.GetName()

	// Get the current status
	status, _, _ := unstructured.NestedMap(obj.Object, "status")
	phase, _, _ := unstructured.NestedString(status, "phase")

	log.Printf("Processing ResearchSession %s with phase %s", name, phase)

	// Only process if status is Pending
	if phase != "Pending" {
		return nil
	}

	// Create a Kubernetes Job for this ResearchSession
	jobName := fmt.Sprintf("%s-job", name)

	// Check if job already exists
	_, err := k8sClient.BatchV1().Jobs(namespace).Get(context.TODO(), jobName, v1.GetOptions{})
	if err == nil {
		log.Printf("Job %s already exists for ResearchSession %s", jobName, name)
		return nil
	}

	// Extract spec information
	spec, _, _ := unstructured.NestedMap(obj.Object, "spec")
	prompt, _, _ := unstructured.NestedString(spec, "prompt")
	websiteURL, _, _ := unstructured.NestedString(spec, "websiteURL")
	timeout, _, _ := unstructured.NestedInt64(spec, "timeout")

	llmSettings, _, _ := unstructured.NestedMap(spec, "llmSettings")
	model, _, _ := unstructured.NestedString(llmSettings, "model")
	temperature, _, _ := unstructured.NestedFloat64(llmSettings, "temperature")
	maxTokens, _, _ := unstructured.NestedInt64(llmSettings, "maxTokens")

	// Create the Job
	job := &batchv1.Job{
		ObjectMeta: v1.ObjectMeta{
			Name:      jobName,
			Namespace: namespace,
			Labels: map[string]string{
				"research-session": name,
				"app":              "claude-runner",
			},
		},
		Spec: batchv1.JobSpec{
			BackoffLimit: int32Ptr(3),
			Template: corev1.PodTemplateSpec{
				ObjectMeta: v1.ObjectMeta{
					Labels: map[string]string{
						"research-session": name,
						"app":              "claude-runner",
					},
				},
				Spec: corev1.PodSpec{
					RestartPolicy: corev1.RestartPolicyNever,
					Containers: []corev1.Container{
						{
							Name:  "claude-runner",
							Image: "claude-runner:latest", // This will be built separately
							Env: []corev1.EnvVar{
								{
									Name:  "RESEARCH_SESSION_NAME",
									Value: name,
								},
								{
									Name:  "RESEARCH_SESSION_NAMESPACE",
									Value: namespace,
								},
								{
									Name:  "PROMPT",
									Value: prompt,
								},
								{
									Name:  "WEBSITE_URL",
									Value: websiteURL,
								},
								{
									Name:  "LLM_MODEL",
									Value: model,
								},
								{
									Name:  "LLM_TEMPERATURE",
									Value: fmt.Sprintf("%.2f", temperature),
								},
								{
									Name:  "LLM_MAX_TOKENS",
									Value: fmt.Sprintf("%d", maxTokens),
								},
								{
									Name:  "TIMEOUT",
									Value: fmt.Sprintf("%d", timeout),
								},
								{
									Name:  "BACKEND_API_URL",
									Value: os.Getenv("BACKEND_API_URL"),
								},
							},
							Resources: corev1.ResourceRequirements{
								Requests: corev1.ResourceList{
									corev1.ResourceCPU:    resource.MustParse("100m"),
									corev1.ResourceMemory: resource.MustParse("256Mi"),
								},
								Limits: corev1.ResourceList{
									corev1.ResourceCPU:    resource.MustParse("1000m"),
									corev1.ResourceMemory: resource.MustParse("1Gi"),
								},
							},
						},
					},
				},
			},
		},
	}

	// Create the job
	_, err = k8sClient.BatchV1().Jobs(namespace).Create(context.TODO(), job, v1.CreateOptions{})
	if err != nil {
		return fmt.Errorf("failed to create job: %v", err)
	}

	log.Printf("Created job %s for ResearchSession %s", jobName, name)

	// Update ResearchSession status to Running
	if err := updateResearchSessionStatus(name, map[string]interface{}{
		"phase":     "Running",
		"message":   "Job created and running",
		"startTime": time.Now().Format(time.RFC3339),
		"jobName":   jobName,
	}); err != nil {
		log.Printf("Failed to update ResearchSession status: %v", err)
		return err
	}

	// Start monitoring the job
	go monitorJob(jobName, name)

	return nil
}

func monitorJob(jobName, sessionName string) {
	for {
		time.Sleep(10 * time.Second)

		job, err := k8sClient.BatchV1().Jobs(namespace).Get(context.TODO(), jobName, v1.GetOptions{})
		if err != nil {
			if errors.IsNotFound(err) {
				log.Printf("Job %s not found, stopping monitoring", jobName)
				return
			}
			log.Printf("Error getting job %s: %v", jobName, err)
			continue
		}

		// Check job status
		if job.Status.Succeeded > 0 {
			log.Printf("Job %s completed successfully", jobName)

			// Update ResearchSession status to Completed
			if err := updateResearchSessionStatus(sessionName, map[string]interface{}{
				"phase":          "Completed",
				"message":        "Job completed successfully",
				"completionTime": time.Now().Format(time.RFC3339),
			}); err != nil {
				log.Printf("Failed to update ResearchSession status: %v", err)
			}
			return
		}

		if job.Status.Failed >= *job.Spec.BackoffLimit {
			log.Printf("Job %s failed after %d attempts", jobName, job.Status.Failed)

			// Get pod logs for error information
			errorMessage := "Job failed"
			if pods, err := k8sClient.CoreV1().Pods(namespace).List(context.TODO(), v1.ListOptions{
				LabelSelector: fmt.Sprintf("job-name=%s", jobName),
			}); err == nil && len(pods.Items) > 0 {
				// Try to get logs from the first pod
				pod := pods.Items[0]
				if logs, err := k8sClient.CoreV1().Pods(namespace).GetLogs(pod.Name, &corev1.PodLogOptions{}).DoRaw(context.TODO()); err == nil {
					errorMessage = fmt.Sprintf("Job failed: %s", string(logs))
					if len(errorMessage) > 500 {
						errorMessage = errorMessage[:500] + "..."
					}
				}
			}

			// Update ResearchSession status to Failed
			if err := updateResearchSessionStatus(sessionName, map[string]interface{}{
				"phase":          "Failed",
				"message":        errorMessage,
				"completionTime": time.Now().Format(time.RFC3339),
			}); err != nil {
				log.Printf("Failed to update ResearchSession status: %v", err)
			}
			return
		}
	}
}

func updateResearchSessionStatus(name string, statusUpdate map[string]interface{}) error {
	gvr := getResearchSessionResource()

	// Get current resource
	obj, err := dynamicClient.Resource(gvr).Namespace(namespace).Get(context.TODO(), name, v1.GetOptions{})
	if err != nil {
		return fmt.Errorf("failed to get ResearchSession %s: %v", name, err)
	}

	// Update status
	if obj.Object["status"] == nil {
		obj.Object["status"] = make(map[string]interface{})
	}

	status := obj.Object["status"].(map[string]interface{})
	for key, value := range statusUpdate {
		status[key] = value
	}

	// Update the resource
	_, err = dynamicClient.Resource(gvr).Namespace(namespace).UpdateStatus(context.TODO(), obj, v1.UpdateOptions{})
	if err != nil {
		return fmt.Errorf("failed to update ResearchSession status: %v", err)
	}

	return nil
}

func int32Ptr(i int32) *int32 {
	return &i
}
