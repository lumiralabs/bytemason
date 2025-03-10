import OpenAI from 'openai';

if (!process.env.OPENAI_API_KEY) {
  throw new Error('Missing OPENAI_API_KEY environment variable');
}

export const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export interface SpecResponse {
  name: string;
  description: string;
  frontend: string[];
  api: {
    [endpoint: string]: {
      [method: string]: string;
    };
  };
  dataModel: {
    [model: string]: {
      [field: string]: string;
    };
  };
  features: string[];
}

export interface GeneratedComponent {
  name: string;
  code: string;
  description: string;
  dependencies: string[];
}

export interface GeneratedApiRoute {
  path: string;
  methods: {
    [method: string]: {
      code: string;
      description: string;
    };
  };
}

export interface GeneratedCode {
  components: GeneratedComponent[];
  apiRoutes: GeneratedApiRoute[];
  types: string;
  utils: string[];
} 