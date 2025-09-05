"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ResearchSession,
  ResearchSessionPhase,
} from "@/types/research-session";
import { Plus, RefreshCw } from "lucide-react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api";

const getPhaseColor = (phase: ResearchSessionPhase) => {
  switch (phase) {
    case "Pending":
      return "bg-yellow-100 text-yellow-800";
    case "Running":
      return "bg-blue-100 text-blue-800";
    case "Completed":
      return "bg-green-100 text-green-800";
    case "Failed":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

export default function HomePage() {
  const [sessions, setSessions] = useState<ResearchSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSessions = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/research-sessions`);
      if (!response.ok) {
        throw new Error("Failed to fetch research sessions");
      }
      const data = await response.json();
      setSessions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
    // Poll for updates every 10 seconds
    const interval = setInterval(fetchSessions, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setLoading(true);
    fetchSessions();
  };

  if (loading && sessions.length === 0) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="animate-spin h-8 w-8" />
          <span className="ml-2">Loading research sessions...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Research Sessions</h1>
          <p className="text-muted-foreground mt-2">
            Manage your Claude research jobs with Browser MCP integration
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleRefresh} disabled={loading}>
            <RefreshCw
              className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
          <Link href="/new">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              New Research Session
            </Button>
          </Link>
        </div>
      </div>

      {error && (
        <Card className="mb-6 border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-700">Error: {error}</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Active Research Sessions</CardTitle>
          <CardDescription>
            Track the status and results of your research jobs
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sessions.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground mb-4">
                No research sessions found
              </p>
              <Link href="/new">
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  Create your first research session
                </Button>
              </Link>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Website</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.map((session) => (
                  <TableRow key={session.metadata.uid}>
                    <TableCell className="font-medium">
                      {session.metadata.name}
                    </TableCell>
                    <TableCell>
                      <Badge
                        className={getPhaseColor(
                          session.status?.phase || "Pending"
                        )}
                      >
                        {session.status?.phase || "Pending"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <a
                        href={session.spec.websiteURL}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline max-w-xs truncate block"
                      >
                        {session.spec.websiteURL}
                      </a>
                    </TableCell>
                    <TableCell>{session.spec.llmSettings.model}</TableCell>
                    <TableCell>
                      {formatDistanceToNow(
                        new Date(session.metadata.creationTimestamp),
                        {
                          addSuffix: true,
                        }
                      )}
                    </TableCell>
                    <TableCell>
                      <Link href={`/session/${session.metadata.name}`}>
                        <Button variant="outline" size="sm">
                          View Details
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
