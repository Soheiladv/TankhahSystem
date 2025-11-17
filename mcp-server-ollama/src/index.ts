#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';

interface OllamaResponse {
  model: string;
  created_at: string;
  response: string;
  done: boolean;
}

interface OllamaCompletion {
  model: string;
  prompt: string;
  stream?: boolean;
}

class OllamaMCPServer {
  private server: Server;
  private ollamaUrl: string;
  private defaultModel: string = 'qwen2.5-coder:1.5b';
  private availableModels: string[] = ['qwen2.5-coder:1.5b', 'llama3.2:1b'];

  constructor() {
    this.ollamaUrl = process.env.OLLAMA_URL || 'http://localhost:11434';
    this.server = new Server(
      {
        name: 'ollama-mcp-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
          resources: {},
          prompts: {},
        },
      }
    );

    this.setupHandlers();
    this.setupErrorHandling();
  }

  private setupHandlers(): void {
    // List available models as resources
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => ({
      resources: this.availableModels.map((model) => ({
        uri: `ollama://model/${model}`,
        mimeType: 'application/json',
        name: `Ollama Model: ${model}`,
        description: `Local Ollama model: ${model}`,
      })),
    }));

    // Read model info
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const modelName = request.params.uri.replace('ollama://model/', '');
      try {
        const response = await axios.get(`${this.ollamaUrl}/api/show`, {
          params: { name: modelName },
        });
        return {
          contents: [
            {
              uri: request.params.uri,
              mimeType: 'application/json',
              text: JSON.stringify(response.data, null, 2),
            },
          ],
        };
      } catch (error: any) {
        throw new Error(`Failed to get model info: ${error.message}`);
      }
    });

    // List tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'ollama_complete',
          description: 'Complete text using an Ollama model. Supports code completion, text generation, and chat.',
          inputSchema: {
            type: 'object',
            properties: {
              prompt: {
                type: 'string',
                description: 'The prompt or text to complete',
              },
              model: {
                type: 'string',
                enum: this.availableModels,
                description: 'Which Ollama model to use',
                default: this.defaultModel,
              },
              system: {
                type: 'string',
                description: 'System message/instructions for the model',
              },
              temperature: {
                type: 'number',
                description: 'Sampling temperature (0-2). Lower = more focused, higher = more creative',
                default: 0.7,
                minimum: 0,
                maximum: 2,
              },
              max_tokens: {
                type: 'number',
                description: 'Maximum tokens to generate',
                default: 2048,
              },
            },
            required: ['prompt'],
          },
        },
        {
          name: 'ollama_list_models',
          description: 'List all available Ollama models on the system',
          inputSchema: {
            type: 'object',
            properties: {},
          },
        },
        {
          name: 'ollama_code_assistant',
          description: 'Get code assistance (completion, explanation, refactoring) using Ollama models',
          inputSchema: {
            type: 'object',
            properties: {
              code: {
                type: 'string',
                description: 'Code to analyze, complete, or refactor',
              },
              language: {
                type: 'string',
                description: 'Programming language',
                default: 'python',
              },
              task: {
                type: 'string',
                enum: ['complete', 'explain', 'refactor', 'debug', 'optimize'],
                description: 'What task to perform',
                default: 'complete',
              },
              model: {
                type: 'string',
                enum: this.availableModels,
                default: 'qwen2.5-coder:1.5b',
                description: 'Model to use (qwen2.5-coder recommended for code)',
              },
            },
            required: ['code'],
          },
        },
        {
          name: 'ollama_chat',
          description: 'Have a conversation with Ollama model',
          inputSchema: {
            type: 'object',
            properties: {
              messages: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    role: {
                      type: 'string',
                      enum: ['user', 'assistant', 'system'],
                    },
                    content: {
                      type: 'string',
                    },
                  },
                  required: ['role', 'content'],
                },
                description: 'Conversation history',
              },
              model: {
                type: 'string',
                enum: this.availableModels,
                default: this.defaultModel,
              },
              temperature: {
                type: 'number',
                default: 0.7,
              },
            },
            required: ['messages'],
          },
        },
      ],
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name } = request.params;
      const args = request.params.arguments;

      try {
        switch (name) {
          case 'ollama_complete':
            return await this.handleComplete(args as any);
          case 'ollama_list_models':
            return await this.handleListModels();
          case 'ollama_code_assistant':
            return await this.handleCodeAssistant(args as any);
          case 'ollama_chat':
            return await this.handleChat(args as any);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error: any) {
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    });

    // Prompts
    this.server.setRequestHandler(ListPromptsRequestSchema, async () => ({
      prompts: [
        {
          name: 'code_review',
          description: 'Review code using Ollama',
          arguments: [
            {
              name: 'code',
              description: 'Code to review',
              required: true,
            },
            {
              name: 'language',
              description: 'Programming language',
              required: false,
            },
          ],
        },
        {
          name: 'explain_code',
          description: 'Explain code using Ollama',
          arguments: [
            {
              name: 'code',
              description: 'Code to explain',
              required: true,
            },
          ],
        },
      ],
    }));

    this.server.setRequestHandler(GetPromptRequestSchema, async (request) => {
      const { name } = request.params;
      const args = request.params.arguments;

      const prompts: Record<string, (args: any) => string> = {
        code_review: (args: any) => {
          const lang = args.language || 'python';
          return `Please review this ${lang} code and provide feedback:\n\n\`\`\`${lang}\n${args.code}\n\`\`\``;
        },
        explain_code: (args: any) => {
          return `Please explain what this code does:\n\n\`\`\`\n${args.code}\n\`\`\``;
        },
      };

      const promptFn = prompts[name];
      if (!promptFn) {
        throw new Error(`Unknown prompt: ${name}`);
      }

      return {
        messages: [
          {
            role: 'user',
            content: promptFn(args),
          },
        ],
      };
    });
  }

  private async handleComplete(args: {
    prompt: string;
    model?: string;
    system?: string;
    temperature?: number;
    max_tokens?: number;
  }): Promise<any> {
    const model = args.model || this.defaultModel;
    const system = args.system || 'You are a helpful AI assistant.';
    const temperature = args.temperature ?? 0.7;

    const prompt = args.system ? `${system}\n\n${args.prompt}` : args.prompt;

    try {
      const response = await axios.post<OllamaResponse>(
        `${this.ollamaUrl}/api/generate`,
        {
          model,
          prompt,
          stream: false,
          options: {
            temperature,
            num_predict: args.max_tokens || 2048,
          },
        }
      );

      return {
        content: [
          {
            type: 'text',
            text: response.data.response,
          },
        ],
      };
    } catch (error: any) {
      throw new Error(`Ollama API error: ${error.message}`);
    }
  }

  private async handleListModels(): Promise<any> {
    try {
      const response = await axios.get(`${this.ollamaUrl}/api/tags`);
      const models = response.data.models?.map((m: any) => m.name) || [];

      return {
        content: [
          {
            type: 'text',
            text: `Available Ollama models:\n${models.map((m: string) => `- ${m}`).join('\n')}`,
          },
        ],
      };
    } catch (error: any) {
      throw new Error(`Failed to list models: ${error.message}`);
    }
  }

  private async handleCodeAssistant(args: {
    code: string;
    language?: string;
    task?: string;
    model?: string;
  }): Promise<any> {
    const model = args.model || 'qwen2.5-coder:1.5b';
    const lang = args.language || 'python';
    const task = args.task || 'complete';

    let prompt = '';
    switch (task) {
      case 'complete':
        prompt = `Complete the following ${lang} code:\n\n\`\`\`${lang}\n${args.code}\n\`\`\``;
        break;
      case 'explain':
        prompt = `Explain what this ${lang} code does:\n\n\`\`\`${lang}\n${args.code}\n\`\`\``;
        break;
      case 'refactor':
        prompt = `Refactor and improve this ${lang} code:\n\n\`\`\`${lang}\n${args.code}\n\`\`\``;
        break;
      case 'debug':
        prompt = `Debug this ${lang} code and explain any issues:\n\n\`\`\`${lang}\n${args.code}\n\`\`\``;
        break;
      case 'optimize':
        prompt = `Optimize this ${lang} code for performance:\n\n\`\`\`${lang}\n${args.code}\n\`\`\``;
        break;
    }

    try {
      const response = await axios.post<OllamaResponse>(
        `${this.ollamaUrl}/api/generate`,
        {
          model,
          prompt,
          stream: false,
          options: {
            temperature: 0.3, // Lower temperature for code
          },
        }
      );

      return {
        content: [
          {
            type: 'text',
            text: response.data.response,
          },
        ],
      };
    } catch (error: any) {
      throw new Error(`Code assistant error: ${error.message}`);
    }
  }

  private async handleChat(args: {
    messages: Array<{ role: string; content: string }>;
    model?: string;
    temperature?: number;
  }): Promise<any> {
    const model = args.model || this.defaultModel;

    // Convert messages to Ollama format
    const ollamaMessages = args.messages.map((msg) => ({
      role: msg.role === 'assistant' ? 'assistant' : 'user',
      content: msg.content,
    }));

    try {
      const response = await axios.post(
        `${this.ollamaUrl}/api/chat`,
        {
          model,
          messages: ollamaMessages,
          stream: false,
          options: {
            temperature: args.temperature || 0.7,
          },
        }
      );

      return {
        content: [
          {
            type: 'text',
            text: response.data.message?.content || response.data.response || 'No response',
          },
        ],
      };
    } catch (error: any) {
      throw new Error(`Chat error: ${error.message}`);
    }
  }

  private setupErrorHandling(): void {
    this.server.onerror = (error) => {
      console.error('[MCP Error]', error);
    };

    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Ollama MCP Server running on stdio');
  }
}

const server = new OllamaMCPServer();
server.run().catch(console.error);

