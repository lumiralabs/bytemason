import { NextResponse } from "next/server";
import { openai } from "@/app/lib/openai";
import { SpecSchema } from "@/app/lib/schemas";

export async function POST(req: Request) {
    try {
        const { prompt } = await req.json();
        console.log('🚀 [Spec Generation] Received prompt:', prompt);

        console.log('📡 [Spec Generation] Making LLM call...');
        const completion = await openai.chat.completions.create({
            model: "gpt-4-turbo-preview",
            messages: [
                {
                    role: "system",
                    content: `You are an expert full-stack developer. Generate a detailed specification for a web application based on the user's prompt.
                    The specification should include:
                    - A clear name and description
                    - Frontend components needed
                    - API endpoints required
                    - Data models
                    - Key features
                    
                    Return the specification in JSON format with the following structure:
                    {
                      "name": "string - application name",
                      "description": "string - detailed description",
                      "frontend": ["string array - list of frontend components"],
                      "api": {"endpoint": {"method": "description"}},
                      "dataModel": {"model": {"field": "type"}},
                      "features": ["string array - list of features"]
                    }`
                },
                {
                    role: "user",
                    content: `Generate a JSON specification for the following app: ${prompt || "Create a todo list application"}`
                }
            ],
            response_format: { type: "json_object" }
        });
        console.log('✅ [Spec Generation] LLM call successful');

        const message = completion.choices[0]?.message;
        if (!message?.content) {
            console.error('❌ [Spec Generation] No valid response');
            throw new Error("Failed to generate specification");
        }

        const parsedContent = JSON.parse(message.content);
        const spec = SpecSchema.parse(parsedContent);
        console.log('✨ [Spec Generation] Validated spec:', spec);

        console.log('🎉 [Spec Generation] Successfully generated spec');
        return NextResponse.json(spec);
    } catch (error) {
        console.error('💥 [Spec Generation] Error:', error);
        return NextResponse.json(
            { error: 'Failed to generate specification. Please try again.' },
            { status: 500 }
        );
    }
}