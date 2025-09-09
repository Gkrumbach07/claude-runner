package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
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
	k8sClient      *kubernetes.Clientset
	dynamicClient  dynamic.Interface
	namespace      string
	builderImage   string
	minioEndpoint  string
	minioAccessKey string
	minioSecretKey string
	baseDomain     string
)

func main() {
	// Initialize Kubernetes clients
	if err := initK8sClients(); err != nil {
		log.Fatalf("Failed to initialize Kubernetes clients: %v", err)
	}

	// Get configuration from environment
	namespace = os.Getenv("NAMESPACE")
	if namespace == "" {
		namespace = "static-hosting"
	}

	builderImage = os.Getenv("BUILDER_IMAGE")
	if builderImage == "" {
		builderImage = "quay.io/example/static-site-builder:latest"
	}

	minioEndpoint = os.Getenv("MINIO_ENDPOINT")
	if minioEndpoint == "" {
		minioEndpoint = "http://minio.minio.svc:9000"
	}

	minioAccessKey = os.Getenv("MINIO_ACCESS_KEY")
	if minioAccessKey == "" {
		minioAccessKey = "admin"
	}

	minioSecretKey = os.Getenv("MINIO_SECRET_KEY")
	if minioSecretKey == "" {
		minioSecretKey = "password123"
	}

	baseDomain = os.Getenv("BASE_DOMAIN")
	if baseDomain == "" {
		baseDomain = "sites.apps.example.com"
	}

	log.Printf("Static Site Hosting Operator starting in namespace: %s", namespace)
	log.Printf("Using builder image: %s", builderImage)
	log.Printf("MinIO endpoint: %s", minioEndpoint)
	log.Printf("Base domain: %s", baseDomain)

	// Start watching StaticSite resources
	go watchStaticSites()

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

func getStaticSiteResource() schema.GroupVersionResource {
	return schema.GroupVersionResource{
		Group:    "hosting.example.com",
		Version:  "v1",
		Resource: "staticsites",
	}
}

func watchStaticSites() {
	gvr := getStaticSiteResource()

	for {
		watcher, err := dynamicClient.Resource(gvr).Namespace(namespace).Watch(context.TODO(), v1.ListOptions{})
		if err != nil {
			log.Printf("Failed to create watcher: %v", err)
			time.Sleep(5 * time.Second)
			continue
		}

		log.Println("Watching for StaticSite events...")

		for event := range watcher.ResultChan() {
			switch event.Type {
			case watch.Added, watch.Modified:
				obj := event.Object.(*unstructured.Unstructured)

				// Add small delay to avoid race conditions
				time.Sleep(100 * time.Millisecond)

				if err := handleStaticSiteEvent(obj); err != nil {
					log.Printf("Error handling StaticSite event: %v", err)
				}
			case watch.Deleted:
				obj := event.Object.(*unstructured.Unstructured)
				siteName := obj.GetName()
				log.Printf("StaticSite %s deleted, cleaning up...", siteName)

				// Clean up MinIO storage
				if err := cleanupSiteStorage(siteName); err != nil {
					log.Printf("Error cleaning up storage for site %s: %v", siteName, err)
				}
			case watch.Error:
				obj := event.Object.(*unstructured.Unstructured)
				log.Printf("Watch error for StaticSite: %v", obj)
			}
		}

		log.Println("Watch channel closed, restarting...")
		watcher.Stop()
		time.Sleep(2 * time.Second)
	}
}

func handleStaticSiteEvent(obj *unstructured.Unstructured) error {
	name := obj.GetName()

	// Verify the resource still exists before processing
	gvr := getStaticSiteResource()
	currentObj, err := dynamicClient.Resource(gvr).Namespace(namespace).Get(context.TODO(), name, v1.GetOptions{})
	if err != nil {
		if errors.IsNotFound(err) {
			log.Printf("StaticSite %s no longer exists, skipping processing", name)
			return nil
		}
		return fmt.Errorf("failed to verify StaticSite %s exists: %v", name, err)
	}

	// Get the current status
	status, _, _ := unstructured.NestedMap(currentObj.Object, "status")
	phase, _, _ := unstructured.NestedString(status, "phase")

	log.Printf("Processing StaticSite %s with phase %s", name, phase)

	// Only process if status is Pending or if we need to rebuild
	if phase != "Pending" && phase != "" {
		return nil
	}

	// Create a build job for this StaticSite
	jobName := fmt.Sprintf("%s-build-%d", name, time.Now().Unix())

	// Check if job already exists
	_, err = k8sClient.BatchV1().Jobs(namespace).Get(context.TODO(), jobName, v1.GetOptions{})
	if err == nil {
		log.Printf("Job %s already exists for StaticSite %s", jobName, name)
		return nil
	}

	// Extract spec information
	spec, _, _ := unstructured.NestedMap(currentObj.Object, "spec")

	// Create the build job
	job, err := createBuildJob(name, jobName, spec)
	if err != nil {
		return fmt.Errorf("failed to create build job spec: %v", err)
	}

	// Update status to Building
	if err := updateStaticSiteStatus(name, map[string]interface{}{
		"phase":   "Building",
		"message": "Build job created and running",
		"jobName": jobName,
	}); err != nil {
		log.Printf("Failed to update StaticSite status to Building: %v", err)
	}

	// Create the job
	_, err = k8sClient.BatchV1().Jobs(namespace).Create(context.TODO(), job, v1.CreateOptions{})
	if err != nil {
		log.Printf("Failed to create job %s: %v", jobName, err)
		// Update status to Failed
		updateStaticSiteStatus(name, map[string]interface{}{
			"phase":   "Failed",
			"message": fmt.Sprintf("Failed to create build job: %v", err),
		})
		return fmt.Errorf("failed to create job: %v", err)
	}

	log.Printf("Created build job %s for StaticSite %s", jobName, name)

	// Start monitoring the job
	go monitorJob(jobName, name)

	return nil
}

func createBuildJob(siteName, jobName string, spec map[string]interface{}) (*batchv1.Job, error) {
	// Extract source configuration
	source, _, _ := unstructured.NestedMap(spec, "source")
	sourceType, _, _ := unstructured.NestedString(source, "type")

	// Extract build configuration
	build, _, _ := unstructured.NestedMap(spec, "build")
	buildEnabled, _, _ := unstructured.NestedBool(build, "enabled")
	buildCommand, _, _ := unstructured.NestedString(build, "command")
	if buildCommand == "" {
		buildCommand = "npm run build"
	}
	outputDir, _, _ := unstructured.NestedString(build, "outputDir")
	if outputDir == "" {
		outputDir = "dist"
	}

	// Prepare environment variables
	env := []corev1.EnvVar{
		{Name: "SITE_NAME", Value: siteName},
		{Name: "SOURCE_TYPE", Value: sourceType},
		{Name: "MINIO_ENDPOINT", Value: minioEndpoint},
		{Name: "MINIO_ACCESS_KEY", Value: minioAccessKey},
		{Name: "MINIO_SECRET_KEY", Value: minioSecretKey},
		{Name: "BUILD_ENABLED", Value: strconv.FormatBool(buildEnabled)},
		{Name: "BUILD_COMMAND", Value: buildCommand},
		{Name: "BUILD_OUTPUT_DIR", Value: outputDir},
	}

	// Add source-specific environment variables
	switch sourceType {
	case "git":
		gitConfig, _, _ := unstructured.NestedMap(source, "git")
		if repository, found, _ := unstructured.NestedString(gitConfig, "repository"); found {
			env = append(env, corev1.EnvVar{Name: "GIT_REPOSITORY", Value: repository})
		}
		if branch, found, _ := unstructured.NestedString(gitConfig, "branch"); found {
			env = append(env, corev1.EnvVar{Name: "GIT_BRANCH", Value: branch})
		}
		if path, found, _ := unstructured.NestedString(gitConfig, "path"); found {
			env = append(env, corev1.EnvVar{Name: "GIT_PATH", Value: path})
		}
	case "docker":
		dockerConfig, _, _ := unstructured.NestedMap(source, "docker")
		if image, found, _ := unstructured.NestedString(dockerConfig, "image"); found {
			env = append(env, corev1.EnvVar{Name: "DOCKER_IMAGE", Value: image})
		}
		if path, found, _ := unstructured.NestedString(dockerConfig, "path"); found {
			env = append(env, corev1.EnvVar{Name: "DOCKER_PATH", Value: path})
		}
	case "url":
		urlConfig, _, _ := unstructured.NestedMap(source, "url")
		if archive, found, _ := unstructured.NestedString(urlConfig, "archive"); found {
			env = append(env, corev1.EnvVar{Name: "URL_ARCHIVE", Value: archive})
		}
		if path, found, _ := unstructured.NestedString(urlConfig, "path"); found {
			env = append(env, corev1.EnvVar{Name: "URL_PATH", Value: path})
		}
	}

	job := &batchv1.Job{
		ObjectMeta: v1.ObjectMeta{
			Name:      jobName,
			Namespace: namespace,
			Labels: map[string]string{
				"static-site": siteName,
				"app":         "static-site-builder",
			},
		},
		Spec: batchv1.JobSpec{
			BackoffLimit:          int32Ptr(3),
			ActiveDeadlineSeconds: int64Ptr(1800), // 30 minute timeout
			Template: corev1.PodTemplateSpec{
				ObjectMeta: v1.ObjectMeta{
					Labels: map[string]string{
						"static-site": siteName,
						"app":         "static-site-builder",
					},
				},
				Spec: corev1.PodSpec{
					RestartPolicy: corev1.RestartPolicyNever,
					Containers: []corev1.Container{
						{
							Name:  "builder",
							Image: builderImage,
							Env:   env,
							Resources: corev1.ResourceRequirements{
								Requests: corev1.ResourceList{
									corev1.ResourceCPU:    resource.MustParse("500m"),
									corev1.ResourceMemory: resource.MustParse("1Gi"),
								},
								Limits: corev1.ResourceList{
									corev1.ResourceCPU:    resource.MustParse("2000m"),
									corev1.ResourceMemory: resource.MustParse("4Gi"),
								},
							},
						},
					},
				},
			},
		},
	}

	return job, nil
}

func monitorJob(jobName, siteName string) {
	log.Printf("Starting job monitoring for %s (site: %s)", jobName, siteName)

	for {
		time.Sleep(10 * time.Second)

		// First check if the StaticSite still exists
		gvr := getStaticSiteResource()
		if _, err := dynamicClient.Resource(gvr).Namespace(namespace).Get(context.TODO(), siteName, v1.GetOptions{}); err != nil {
			if errors.IsNotFound(err) {
				log.Printf("StaticSite %s no longer exists, stopping job monitoring for %s", siteName, jobName)
				return
			}
			log.Printf("Error checking StaticSite %s existence: %v", siteName, err)
		}

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

			// Generate site URL
			siteURL := generateSiteURL(siteName)

			// Update StaticSite status to Ready
			updateStaticSiteStatus(siteName, map[string]interface{}{
				"phase":         "Ready",
				"message":       "Site built and deployed successfully",
				"url":           siteURL,
				"lastBuildTime": time.Now().Format(time.RFC3339),
			})
			return
		}

		if job.Status.Failed >= *job.Spec.BackoffLimit {
			log.Printf("Job %s failed after %d attempts", jobName, job.Status.Failed)

			// Get pod logs for error information
			errorMessage := "Build failed"
			if pods, err := k8sClient.CoreV1().Pods(namespace).List(context.TODO(), v1.ListOptions{
				LabelSelector: fmt.Sprintf("job-name=%s", jobName),
			}); err == nil && len(pods.Items) > 0 {
				// Try to get logs from the first pod
				pod := pods.Items[0]
				if logs, err := k8sClient.CoreV1().Pods(namespace).GetLogs(pod.Name, &corev1.PodLogOptions{}).DoRaw(context.TODO()); err == nil {
					errorMessage = fmt.Sprintf("Build failed: %s", string(logs))
					if len(errorMessage) > 500 {
						errorMessage = errorMessage[:500] + "..."
					}
				}
			}

			// Update StaticSite status to Failed
			updateStaticSiteStatus(siteName, map[string]interface{}{
				"phase":   "Failed",
				"message": errorMessage,
			})
			return
		}
	}
}

func updateStaticSiteStatus(name string, statusUpdate map[string]interface{}) error {
	gvr := getStaticSiteResource()

	// Get current resource
	obj, err := dynamicClient.Resource(gvr).Namespace(namespace).Get(context.TODO(), name, v1.GetOptions{})
	if err != nil {
		if errors.IsNotFound(err) {
			log.Printf("StaticSite %s no longer exists, skipping status update", name)
			return nil
		}
		return fmt.Errorf("failed to get StaticSite %s: %v", name, err)
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
		if errors.IsNotFound(err) {
			log.Printf("StaticSite %s was deleted during status update, skipping", name)
			return nil
		}
		return fmt.Errorf("failed to update StaticSite status: %v", err)
	}

	return nil
}

func generateSiteURL(siteName string) string {
	// Clean site name for URL
	cleanName := strings.ToLower(siteName)
	cleanName = strings.ReplaceAll(cleanName, "_", "-")
	
	return fmt.Sprintf("https://%s.%s", cleanName, baseDomain)
}

func cleanupSiteStorage(siteName string) error {
	// This would typically use MinIO client to remove the site directory
	// For now, we'll just log the cleanup action
	log.Printf("Would clean up MinIO storage for site: %s", siteName)
	
	// TODO: Implement actual MinIO cleanup
	// mc rm --recursive myminio/sites/<siteName>/
	
	return nil
}

var (
	boolPtr  = func(b bool) *bool { return &b }
	int32Ptr = func(i int32) *int32 { return &i }
	int64Ptr = func(i int64) *int64 { return &i }
)