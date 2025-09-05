export type ResearchSessionPhase = "Pending" | "Running" | "Completed" | "Failed";

export type LLMSettings = {
	model: string;
	temperature: number;
	maxTokens: number;
};

export type ResearchSessionSpec = {
	prompt: string;
	websiteURL: string;
	llmSettings: LLMSettings;
	timeout: number;
};

export type ResearchSessionStatus = {
	phase: ResearchSessionPhase;
	message?: string;
	startTime?: string;
	completionTime?: string;
	jobName?: string;
	finalOutput?: string;
};

export type ResearchSession = {
	metadata: {
		name: string;
		namespace: string;
		creationTimestamp: string;
		uid: string;
	};
	spec: ResearchSessionSpec;
	status?: ResearchSessionStatus;
};

export type CreateResearchSessionRequest = {
	prompt: string;
	websiteURL: string;
	llmSettings?: Partial<LLMSettings>;
	timeout?: number;
};
