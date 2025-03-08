'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import Image from 'next/image'

export default function BlogPost() {
  const wordCount = 925

  return (
    <main className="min-h-screen bg-black text-white/90">
      

      {/* Gradient Header */}
      <div className="relative h-72 w-full overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-green-500/10" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-cyan-900/30 via-black to-black" />
        
        <div className="relative z-10 max-w-4xl mx-auto px-4 pt-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="flex items-center gap-2 mb-4">
              <span className="text-sm text-cyan-300/70">March 7, 2024</span>
              <span className="text-white/20">•</span>
              <span className="text-sm text-cyan-300/70">{wordCount} words</span>
            </div>
            <h1 className="font-pixel text-4xl md:text-5xl lg:text-6xl mb-4 bg-gradient-to-r from-cyan-300/90 to-green-300/90 bg-clip-text text-transparent">
              Building ByteMason: The Tool That Builds Apps for You
            </h1>
          </motion.div>
        </div>
      </div>

      {/* Blog Content */}
      <motion.article 
        className="max-w-4xl mx-auto px-4 pt-12 space-y-8 pb-20"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        <p className="text-xl text-white/70 leading-relaxed">
          Welcome reader! This time, we took it all the way: building an app that, in turn, builds entire applications. We call it <span className="text-cyan-300/90">ByteMason</span>, and it takes a simple prompt—like "build me a to-do list app with user authentication"—and turns it into a fully functional Next.js 14 project with Supabase integration, authentication, and more.
        </p>

        <section>
          <h2 className="font-pixel text-2xl md:text-3xl text-cyan-300/90 mb-4">
            Why We Built ByteMason
          </h2>
          <p className="text-white/70 leading-relaxed">
            Our initial goal was to recreate a mini version of one of our apps, <Link href="https://lumeon.app" target="_blank" rel="noopener noreferrer" className="text-green-300/90 hover:text-green-200/90 transition-colors">Lumeon</Link>, using nothing but a prompt. We wanted to see if we could streamline the entire process of building a Supabase-backed Next.js application, from planning to deployment.
          </p>
          <p className="text-white/70 leading-relaxed mt-4">
            At first, we imagined a sleek UI that anyone could click through. However, we started with a CLI tool to reduce risk and keep things practical. That pivot gave us a clear, simple foundation to test our ideas and learn from mistakes before building out a web interface.
          </p>
        </section>

        <section>
          <h2 className="font-pixel text-2xl md:text-3xl text-cyan-300/90 mb-4">
            Our Development Process
          </h2>
          <p className="text-white/70 leading-relaxed mb-4">
            At Lumira Labs, we follow three steps for every major project:
          </p>
          <ol className="space-y-4 text-white/70">
            <li className="flex gap-3">
              <span className="text-green-300/90">1.</span>
              <div>
                <strong className="text-green-300/90">Research & Specification</strong>
                <p className="mt-1">We spent a couple of weeks exploring how AI agents work, what tools were out there, and how to make our own.</p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="text-green-300/90">2.</span>
              <div>
                <strong className="text-green-300/90">Prototype</strong>
                <p className="mt-1">We built a minimal app to see if the concept was viable.</p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="text-green-300/90">3.</span>
              <div>
                <strong className="text-green-300/90">Development</strong>
                <p className="mt-1">We built the CLI, worked out the bugs, and scaled it into a stable product.</p>
              </div>
            </li>
          </ol>
          <p className="text-white/70 leading-relaxed mt-4">
            In the Research phase, we discovered an agent library—Codegen—that seemed powerful. But we quickly realized these tools were too opaque, costing us time and money without us truly knowing how they operated internally. So, we decided to build our workflow from scratch, giving us total control and insight into every step.
          </p>
        </section>

        <section>
          <h2 className="font-pixel text-2xl md:text-3xl text-cyan-300/90 mb-4">
            How It Works
          </h2>
          <div className="relative w-full h-64 md:h-80 my-8 rounded-lg overflow-hidden bg-white/[0.03] border border-white/[0.05]">
            <Image
              src="/arch.png"
              alt="High level overview of the system"
              fill
              className="object-contain"
            />
            <div className="absolute bottom-0 left-0 right-0 bg-black/60 backdrop-blur-sm p-2">
              <p className="text-center text-white/70 text-sm">High level overview of the system</p>
            </div>
          </div>
          <p className="text-white/70 leading-relaxed">
            ByteMason is driven by a simple command sequence. You start by creating a project folder:
          </p>
          <div className="bg-white/[0.03] p-4 rounded-lg my-4 border border-white/[0.05]">
            <code className="text-green-300/90">berry new Project-Name</code>
          </div>
          <p className="text-white/70 leading-relaxed mt-4">
            Then you provide a prompt that describes what you want to build:
          </p>
          <div className="bg-white/[0.03] p-4 rounded-lg my-4 border border-white/[0.05]">
            <code className="text-green-300/90">berry plan "PROMPT"</code>
          </div>
          <p className="text-white/70 leading-relaxed">
            When you run this command, we process your request and show you exactly how it works behind the scenes.
          </p>
        </section>

        <section>
          <h2 className="font-pixel text-2xl md:text-3xl text-cyan-300/90 mb-4">
            Understanding What You Want
          </h2>
          <p className="text-white/70 leading-relaxed">
            When you provide that prompt, ByteMason first processes it through the <span className="text-green-300/90">ProjectBuilder.understand_intent()</span> method:
          </p>
          <ol className="list-decimal pl-6 mt-4 space-y-2 text-white/70">
            <li>Your prompt is sent to Claude 3.5 Sonnet with a specialized system prompt</li>
            <li className="space-y-2">
              The AI extracts structured information into an Intent object containing:
              <ul className="list-disc pl-6 space-y-1">
                <li>App name and purpose</li>
                <li>User types (roles)</li>
                <li>Core features with priority and complexity</li>
                <li>Data entities and attributes</li>
                <li>Authentication requirements</li>
                <li>Integration requirements</li>
                <li>Technical constraints</li>
              </ul>
            </li>
          </ol>
          <p className="text-white/70 leading-relaxed mt-4">
            This transforms your idea—even if it's a bit vague—into something structured we can work with, without adding features you didn't ask for.
          </p>
        </section>

        <section>
          <h2 className="font-pixel text-2xl md:text-3xl text-cyan-300/90 mb-4">
            Planning Your Project
          </h2>
          <p className="text-white/70 leading-relaxed">
            A specification file is generated from your prompt and saved in the specs/ folder. This happens through our <span className="text-green-300/90">create_spec()</span> process:
          </p>
          <ol className="list-decimal pl-6 mt-4 space-y-2 text-white/70">
            <li>The Intent object is passed to the AI with a prompt that includes project architecture patterns</li>
            <li className="space-y-2">
              It returns a structured ProjectSpec containing:
              <ul className="list-disc pl-6 space-y-1">
                <li>Detailed pages layout and navigation flow</li>
                <li>Component hierarchy with descriptions</li>
                <li>API routes with methods and purposes</li>
                <li>Database tables with relationships</li>
              </ul>
            </li>
          </ol>
        </section>

        <section>
          <h2 className="font-pixel text-2xl md:text-3xl text-cyan-300/90 mb-4">
            Setting Up Your Database
          </h2>
          <div className="bg-white/[0.03] p-4 rounded-lg my-4 border border-white/[0.05]">
            <code className="text-green-300/90">berry db setup spec_path // to setup supabase keys and generate migrations</code>
          </div>
          <div className="bg-white/[0.03] p-4 rounded-lg my-4 border border-white/[0.05]">
            <code className="text-green-300/90">berry db push // to push migrations to remote supabase project</code>
          </div>
          <p className="text-white/70 leading-relaxed mt-4">
            Here, the SupabaseSetupAgent:
          </p>
          <ol className="list-decimal pl-6 mt-4 space-y-2 text-white/70">
            <li>Generates SQL migration scripts directly from your project spec</li>
            <li>Initializes a Supabase project connection</li>
            <li>Sets up proper environment variables</li>
            <li>Applies migrations to create your tables</li>
          </ol>
          <p className="text-white/70 leading-relaxed mt-4">
            We use standard Supabase CLI commands, not mysterious API calls, so you see exactly what's happening with your data.
          </p>
        </section>

        <section>
          <h2 className="font-pixel text-2xl md:text-3xl text-cyan-300/90 mb-4">
            Building Your Code Layer by Layer
          </h2>
          <div className="bg-white/[0.03] p-4 rounded-lg my-4 border border-white/[0.05]">
            <code className="text-green-300/90">berry code spec_path</code>
          </div>
          <p className="text-white/70 leading-relaxed">
            This is where things happen. Our CodeAgent generates code in a context-aware sequence:
          </p>
          <ol className="space-y-4 text-white/70 mt-4">
            <li className="flex gap-3">
              <span className="text-green-300/90">1.</span>
              <div>
                <strong className="text-green-300/90">API Routes First</strong>: Generates backend routes with database access
                <ul className="list-disc pl-6 mt-2 space-y-1">
                  <li>Each route is properly typed with error handling</li>
                  <li>Security best practices are built in</li>
                </ul>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="text-green-300/90">2.</span>
              <div>
                <strong className="text-green-300/90">Components with API Context</strong>: Creates React components that know about your API
                <ul className="list-disc pl-6 mt-2 space-y-1">
                  <li>Components are separated into client and server components</li>
                  <li>Client components implement optimistic UI patterns</li>
                </ul>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="text-green-300/90">3.</span>
              <div>
                <strong className="text-green-300/90">Pages with Full Context</strong>: Builds app pages that know about both APIs and components
                <ul className="list-disc pl-6 mt-2 space-y-1">
                  <li>Uses proper Next.js 14 App Router conventions</li>
                  <li>Everything is connected correctly</li>
                </ul>
              </div>
            </li>
          </ol>
          <p className="text-white/70 leading-relaxed mt-4">
            ByteMason also sets up any shadcn UI components it detects in the generated code.
          </p>
        </section>

        <section>
          <h2 className="font-pixel text-2xl md:text-3xl text-cyan-300/90 mb-4">
            Automatic Repair Agent
          </h2>
          <div className="bg-white/[0.03] p-4 rounded-lg my-4 border border-white/[0.05]">
            <code className="text-green-300/90">berry repair</code>
          </div>
          <p className="text-white/70 leading-relaxed">
            When you run this, ByteMason:
          </p>
          <ol className="list-decimal pl-6 mt-4 space-y-2 text-white/70">
            <li>Tries to build your application and captures any errors</li>
            <li>Analyzes the build output to understand what went wrong</li>
            <li className="space-y-2">
              Uses a set of tools to fix each problem one by one:
              <ul className="list-disc pl-6 space-y-1">
                <li>Reads files to check current content</li>
                <li>Writes fixes where needed</li>
                <li>Analyzes dependencies and import relationships</li>
                <li>Explores your project structure</li>
              </ul>
            </li>
          </ol>
          <p className="text-white/70 leading-relaxed mt-4">
            It repeats this process until your build passes, with no human intervention required.
          </p>
          <p className="text-white/70 leading-relaxed mt-4">
            You get all the power of AI assistance without giving up control or understanding of your own project.
          </p>
        </section>

        <section>
          <h2 className="font-pixel text-2xl md:text-3xl text-cyan-300/90 mb-4">
            Key Lessons
          </h2>
          <ol className="space-y-6 text-white/70">
            <li className="flex gap-3">
              <span className="text-green-300/90">1.</span>
              <div>
                <strong className="text-green-300/90">Keep It Simple</strong>
                <p className="mt-1">Building our own code generation and repair workflow turned out to be more transparent than relying on a complex library we didn't fully understand.</p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="text-green-300/90">2.</span>
              <div>
                <strong className="text-green-300/90">Model Choice Matters</strong>
                <p className="mt-1">We tested both GPT-4o and Anthropic's Sonnet 3.5 models for code generation. Sonnet 3.5 had fewer errors in its outputs, though we occasionally hit rate limits.</p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="text-green-300/90">3.</span>
              <div>
                <strong className="text-green-300/90">Agentic Workflows Are Powerful</strong>
                <p className="mt-1">Agents that can plan, generate, and repair code can handle a surprising amount of complexity—much more than a simple "code spit out" approach.</p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="text-green-300/90">4.</span>
              <div>
                <strong className="text-green-300/90">From CLI to Next Steps</strong>
                <p className="mt-1">Starting with a CLI gave us clarity on what works.</p>
              </div>
            </li>
          </ol>
        </section>

        <section className="pb-20">
          <h2 className="font-pixel text-2xl md:text-3xl text-cyan-300/90 mb-4">
            The Outcome
          </h2>
          <p className="text-white/70 leading-relaxed">
            In the end, we asked ByteMason to build a simple <span className="text-green-300/90">to-do list</span> application. It set up the database, wrote the code, handled authentication, and even fixed its build errors—no human intervention required, beyond the initial prompt.
          </p>
          <p className="text-white/70 leading-relaxed mt-4">
            It's part of the story toward a future where building full-stack apps could be as easy as writing a quick note about what you want.
          </p>
        </section>
      </motion.article>
    </main>
  )
}
