"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { formatDistanceToNow, format } from "date-fns";
import Link from "next/link";
import {
  ArrowLeft,
  RefreshCw,
  ExternalLink,
  Clock,
  Globe,
  Brain,
  Square,
  Trash2,
} from "lucide-react";

// PatternFly imports
import { Truncate } from "@patternfly/react-core";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ResearchSession,
  ResearchSessionPhase,
} from "@/types/research-session";

import { getApiUrl } from "@/lib/config";

const getPhaseColor = (phase: ResearchSessionPhase) => {
  switch (phase) {
    case "Pending":
      return "bg-yellow-100 text-yellow-800";
    case "Creating":
      return "bg-blue-100 text-blue-800";
    case "Running":
      return "bg-blue-100 text-blue-800";
    case "Completed":
      return "bg-green-100 text-green-800";
    case "Failed":
      return "bg-red-100 text-red-800";
    case "Stopped":
      return "bg-gray-100 text-gray-800";
    case "Error":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

export default function SessionDetailPage() {
  const params = useParams();
  const sessionName = params.name as string;

  const [session, setSession] = useState<ResearchSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchSession = useCallback(async () => {
    try {
      const response = await fetch(
        `${getApiUrl()}/research-sessions/${sessionName}`
      );
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("Research session not found");
        }
        throw new Error("Failed to fetch research session");
      }
      const data = await response.json();
      setSession(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [sessionName]);

  useEffect(() => {
    if (sessionName) {
      fetchSession();
      // Poll for updates every 5 seconds if the session is still running
      const interval = setInterval(() => {
        if (
          session?.status?.phase === "Pending" ||
          session?.status?.phase === "Running"
        ) {
          fetchSession();
        }
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [sessionName, session?.status?.phase, fetchSession]);

  const handleRefresh = () => {
    setLoading(true);
    fetchSession();
  };

  const handleStop = async () => {
    if (!session) return;
    setActionLoading("stopping");
    try {
      const apiUrl = getApiUrl();
      const response = await fetch(
        `${apiUrl}/research-sessions/${sessionName}/stop`,
        {
          method: "POST",
        }
      );
      if (!response.ok) {
        throw new Error("Failed to stop session");
      }
      await fetchSession(); // Refresh the session data
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to stop session");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async () => {
    if (!session) return;

    if (
      !confirm(
        `Are you sure you want to delete research session "${sessionName}"? This action cannot be undone.`
      )
    ) {
      return;
    }

    setActionLoading("deleting");
    try {
      const apiUrl = getApiUrl();
      const response = await fetch(
        `${apiUrl}/research-sessions/${sessionName}/delete`,
        {
          method: "DELETE",
        }
      );
      if (!response.ok) {
        throw new Error("Failed to delete session");
      }
      // Redirect back to home after successful deletion
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete session");
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="animate-spin h-8 w-8" />
          <span className="ml-2">Loading research session...</span>
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center mb-6">
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Sessions
            </Button>
          </Link>
        </div>
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-700">
              Error: {error || "Session not found"}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <Link href="/">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Sessions
          </Button>
        </Link>
        <div className="flex items-center gap-4">
          <Button variant="outline" onClick={handleRefresh} disabled={loading}>
            <RefreshCw
              className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>

          {/* Action buttons based on session status */}
          {session &&
            (() => {
              const phase = session.status?.phase || "Pending";

              if (actionLoading) {
                return (
                  <Button variant="outline" disabled>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    {actionLoading}
                  </Button>
                );
              }

              const buttons = [];

              // Stop button for Pending/Creating/Running sessions
              if (
                phase === "Pending" ||
                phase === "Creating" ||
                phase === "Running"
              ) {
                buttons.push(
                  <Button key="stop" variant="secondary" onClick={handleStop}>
                    <Square className="w-4 h-4 mr-2" />
                    Stop
                  </Button>
                );
              }

              // Delete button for all sessions (except running/creating)
              if (phase !== "Running" && phase !== "Creating") {
                buttons.push(
                  <Button
                    key="delete"
                    variant="destructive"
                    onClick={handleDelete}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </Button>
                );
              }

              return buttons;
            })()}
        </div>
      </div>

      <div className="space-y-6">
        {/* Header */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-2xl">
                  {session.metadata.name}
                </CardTitle>
                <CardDescription>
                  Created{" "}
                  {formatDistanceToNow(
                    new Date(session.metadata.creationTimestamp),
                    { addSuffix: true }
                  )}
                </CardDescription>
              </div>
              <Badge
                className={getPhaseColor(session.status?.phase || "Pending")}
              >
                {session.status?.phase || "Pending"}
              </Badge>
            </div>
          </CardHeader>
        </Card>

        {/* Session Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Brain className="w-5 h-5 mr-2" />
                Research Prompt
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm">
                {session.spec.prompt}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Globe className="w-5 h-5 mr-2" />
                Target Website
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center">
                    <Truncate
                      content={session.spec.websiteURL}
                      tooltipPosition="top"
                      position="end"
                      className="text-blue-600 hover:underline"
                    />
                    <a
                      href={session.spec.websiteURL}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-2 flex-shrink-0"
                    >
                      <ExternalLink className="w-4 h-4 text-blue-600 hover:text-blue-800" />
                    </a>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p className="font-semibold">Model</p>
                <p className="text-muted-foreground">
                  {session.spec.llmSettings.model}
                </p>
              </div>
              <div>
                <p className="font-semibold">Temperature</p>
                <p className="text-muted-foreground">
                  {session.spec.llmSettings.temperature}
                </p>
              </div>
              <div>
                <p className="font-semibold">Max Tokens</p>
                <p className="text-muted-foreground">
                  {session.spec.llmSettings.maxTokens}
                </p>
              </div>
              <div>
                <p className="font-semibold">Timeout</p>
                <p className="text-muted-foreground">{session.spec.timeout}s</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Status Information */}
        {session.status && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Clock className="w-5 h-5 mr-2" />
                Execution Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {session.status.message && (
                  <div>
                    <p className="font-semibold text-sm">Status Message</p>
                    <p className="text-sm text-muted-foreground">
                      {session.status.message}
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  {session.status.startTime && (
                    <div>
                      <p className="font-semibold">Started</p>
                      <p className="text-muted-foreground">
                        {format(new Date(session.status.startTime), "PPp")}
                      </p>
                    </div>
                  )}

                  {session.status.completionTime && (
                    <div>
                      <p className="font-semibold">Completed</p>
                      <p className="text-muted-foreground">
                        {format(new Date(session.status.completionTime), "PPp")}
                      </p>
                    </div>
                  )}

                  {session.status.jobName && (
                    <div>
                      <p className="font-semibold">Kubernetes Job</p>
                      <p className="text-muted-foreground font-mono text-xs">
                        {session.status.jobName}
                      </p>
                    </div>
                  )}

                  {session.status.cost && (
                    <div>
                      <p className="font-semibold">Cost</p>
                      <p className="text-muted-foreground">
                        ${session.status.cost.toFixed(4)}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Real-time Messages Progress - PatternFly Chatbot Style */}
        {((session.status?.messages && session.status.messages.length > 0) ||
          session.status?.phase === "Running" ||
          session.status?.phase === "Pending" ||
          session.status?.phase === "Creating") && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Research Progress</span>
                <Badge variant="secondary">
                  {session.status?.messages?.length || 0} message
                  {(session.status?.messages?.length || 0) !== 1 ? "s" : ""}
                </Badge>
              </CardTitle>
              <CardDescription>Live analysis from Claude AI</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="max-h-96 overflow-y-auto space-y-4 bg-gray-50 rounded-lg p-4">
                {/* Display all existing messages */}
                {session.status?.messages?.map((message, index) => (
                  <div key={index} className="mb-4">
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                          <span className="text-white text-xs font-semibold">
                            AI
                          </span>
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="bg-white rounded-lg border shadow-sm p-3">
                          <div className="flex items-center justify-between mb-2">
                            <Badge variant="outline" className="text-xs">
                              Claude AI
                            </Badge>
                            <span className="text-xs text-gray-500">
                              Message {index + 1}
                            </span>
                          </div>
                          <div className="text-sm text-gray-800 prose prose-sm max-w-none">
                            <Truncate
                              content={message}
                              tooltipPosition="top"
                              position="end"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                {/* Show loading message if still processing */}
                {(session.status?.phase === "Running" ||
                  session.status?.phase === "Pending" ||
                  session.status?.phase === "Creating") && (
                  <div className="mb-4">
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center animate-pulse">
                          <span className="text-white text-xs font-semibold">
                            AI
                          </span>
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="bg-white rounded-lg border shadow-sm p-3">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge
                              variant="outline"
                              className="text-xs animate-pulse"
                            >
                              Claude AI
                            </Badge>
                            <span className="text-xs text-gray-500">
                              Analyzing...
                            </span>
                          </div>
                          <div className="text-sm text-gray-600">
                            {session.status?.phase === "Pending"
                              ? "Research session is queued and waiting to start..."
                              : session.status?.phase === "Creating"
                              ? "Creating research environment..."
                              : "Analyzing the website and generating insights..."}
                            <div className="flex items-center mt-2">
                              <div className="flex space-x-1">
                                <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce"></div>
                                <div
                                  className="w-1 h-1 bg-blue-500 rounded-full animate-bounce"
                                  style={{ animationDelay: "0.1s" }}
                                ></div>
                                <div
                                  className="w-1 h-1 bg-blue-500 rounded-full animate-bounce"
                                  style={{ animationDelay: "0.2s" }}
                                ></div>
                              </div>
                              <span className="ml-2 text-xs text-gray-400">
                                Thinking...
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Show empty state if no messages yet */}
                {(!session.status?.messages ||
                  session.status.messages.length === 0) &&
                  session.status?.phase !== "Running" &&
                  session.status?.phase !== "Pending" &&
                  session.status?.phase !== "Creating" && (
                    <div className="text-center py-8 text-gray-500">
                      <Brain className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p>No messages yet</p>
                    </div>
                  )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Research Results */}
        {session.status?.finalOutput && (
          <Card>
            <CardHeader>
              <CardTitle>Research Results</CardTitle>
              <CardDescription>
                Claude&apos;s analysis of the target website
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="bg-gray-50 rounded-lg p-4">
                <pre className="whitespace-pre-wrap text-sm font-mono overflow-x-auto">
                  {session.status.finalOutput}
                </pre>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
