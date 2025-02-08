import { NextResponse } from "next/server";
import { openai } from "@/app/lib/openai";
import { GeneratedCodeSchema } from "@/app/lib/schemas";

interface FileStructure {
  [key: string]: {
    file?: { contents: string };
    directory?: FileStructure;
  };
}

function sanitizeRoutePath(path: string): string {
  // Convert dynamic route parameters from {param} to [param]
  // e.g., tasks/{taskId} becomes tasks/[taskId]
  return path.replace(/\{(\w+)\}/g, '[$1]');
}

export async function POST(req: Request) {
  try {
    const { spec } = await req.json();
    console.log('🚀 [Code Generation] Received spec:', spec);

    console.log('📡 [Code Generation] Making LLM call...');
    const completion = await openai.chat.completions.create({
      model: "gpt-4-turbo-preview",
      messages: [
        {
          role: "system",
          content: `You are an expert full-stack developer. Generate code for a Next.js application based on the provided specification.
          Follow these guidelines:
          - Use Next.js 13+ App Router conventions
          - Create React components with TypeScript
          - Generate API routes using Next.js route handlers
          - Include proper TypeScript types
          - Add utility functions as needed
          
          Return the generated code in JSON format with the following structure:
          {
            "components": [
              {
                "name": "string - component name",
                "code": "string - component implementation",
                "description": "string - component description",
                "dependencies": ["string array - component dependencies"]
              }
            ],
            "apiRoutes": [
              {
                "path": "string - route path",
                "methods": {
                  "methodName": {
                    "code": "string - method implementation",
                    "description": "string - method description"
                  }
                }
              }
            ],
            "types": "string - TypeScript type definitions",
            "utils": ["string array - utility functions"]
          }`
        },
        {
          role: "user",
          content: `Generate code for the following specification: ${JSON.stringify(spec, null, 2)}`
        }
      ],
      response_format: { type: "json_object" }
    });
    console.log('✅ [Code Generation] LLM call successful');

    const message = completion.choices[0]?.message;
    if (!message?.content) {
      console.error('❌ [Code Generation] No valid response');
      throw new Error("Failed to generate code");
    }

    const parsedContent = JSON.parse(message.content);
    const generatedCode = GeneratedCodeSchema.parse(parsedContent);
    console.log('✨ [Code Generation] Validated generated code');

    console.log('🔨 [Code Generation] Building file structure...');
    // Convert the generated code into the file structure
    const files: FileStructure = {
      'package.json': {
        file: {
          contents: JSON.stringify({
            name: spec.name.toLowerCase().replace(/\s+/g, '-'),
            type: 'module',
            scripts: {
              dev: 'next dev',
              build: 'next build',
              start: 'next start'
            },
            dependencies: {
              next: '^14.0.0',
              react: '^18.2.0',
              'react-dom': '^18.2.0',
              '@types/react': '^18.2.0',
              '@types/react-dom': '^18.2.0',
              typescript: '^5.0.0',
              'zod': '^3.22.0'
            }
          }, null, 2)
        }
      },
      'types': {
        directory: {
          'index.ts': {
            file: {
              contents: generatedCode.types
            }
          }
        }
      },
      'utils': {
        directory: generatedCode.utils.reduce((acc, util, index) => {
          acc[`util${index + 1}.ts`] = {
            file: { contents: util }
          };
          return acc;
        }, {} as FileStructure)
      },
      'app': {
        directory: {
          'api': {
            directory: generatedCode.apiRoutes.reduce((acc, route) => {
              // Convert {param} to [param] in route paths
              const routePath = sanitizeRoutePath(route.path.replace('/api/', ''));
              const routeMethods = Object.entries(route.methods)
                .map(([method, { code }]) => `
export async function ${method}(request: Request) {
${code}
}`)
                .join('\n\n');
              
              if (routeMethods) {
                // Create nested directories for the route path
                const pathParts = routePath.split('/');
                let currentPath = acc;
                
                // Create directories for each path segment
                pathParts.forEach((part, index) => {
                  if (index === pathParts.length - 1) {
                    // Last part - create route.ts file
                    currentPath[part] = {
                      directory: {
                        'route.ts': {
                          file: {
                            contents: `
import { NextResponse } from 'next/server';
${routeMethods}
`
                          }
                        }
                      }
                    };
                  } else {
                    // Create intermediate directory
                    if (!currentPath[part]) {
                      currentPath[part] = { directory: {} };
                    }
                    currentPath = currentPath[part].directory!;
                  }
                });
              }
              return acc;
            }, {} as FileStructure)
          },
          'page.tsx': {
            file: {
              contents: `
import { ${generatedCode.components.map(c => c.name).join(', ')} } from '@/components';

export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <h1 className="text-3xl font-bold mb-8">${spec.name}</h1>
      ${generatedCode.components.map(c => `<${c.name} />`).join('\n      ')}
    </main>
  );
}`
            }
          }
        }
      },
      'components': {
        directory: generatedCode.components.reduce((acc, component) => {
          acc[`${component.name}.tsx`] = {
            file: { contents: component.code }
          };
          return acc;
        }, {} as FileStructure)
      }
    };

    console.log('🎉 [Code Generation] Successfully generated file structure');
    console.log('📁 [Code Generation] Generated files:', Object.keys(files));
    return NextResponse.json(files);
  } catch (error) {
    console.error('💥 [Code Generation] Error:', error);
    return NextResponse.json(
      { error: 'Failed to generate code. Please try again.' },
      { status: 500 }
    );
  }
} 