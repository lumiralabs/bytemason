import { z } from 'zod';

// Spec Schema
export const SpecSchema = z.object({
  name: z.string().describe("The name of the application"),
  description: z.string().describe("Detailed description of the application"),
  frontend: z.array(z.string()).describe("List of frontend components needed"),
  api: z.record(z.record(z.string())).describe("API endpoints and their methods"),
  dataModel: z.record(z.record(z.string())).describe("Data models and their fields"),
  features: z.array(z.string()).describe("List of key features")
});

// Code Generation Schemas
const ApiMethodSchema = z.object({
  code: z.string().describe("The implementation code for the method"),
  description: z.string().describe("Description of what the method does")
});

const ApiRouteSchema = z.object({
  path: z.string().describe("The route path"),
  methods: z.record(ApiMethodSchema).describe("HTTP methods for this route")
});

const ComponentSchema = z.object({
  name: z.string().describe("Component name"),
  code: z.string().describe("Component implementation"),
  description: z.string().describe("Component description"),
  dependencies: z.array(z.string()).describe("Component dependencies")
});

export const GeneratedCodeSchema = z.object({
  components: z.array(ComponentSchema).describe("React components"),
  apiRoutes: z.array(ApiRouteSchema).describe("API routes"),
  types: z.string().describe("TypeScript type definitions"),
  utils: z.array(z.string()).describe("Utility functions")
});

export type Spec = z.infer<typeof SpecSchema>;
export type GeneratedCode = z.infer<typeof GeneratedCodeSchema>; 