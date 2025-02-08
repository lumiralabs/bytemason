'use client';

import { useState, useRef } from 'react';
import { WebContainer } from '@webcontainer/api';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { vs2015 } from 'react-syntax-highlighter/dist/cjs/styles/hljs';

interface Spec {
  name: string;
  description: string;
  frontend: string[];
  api: {
    [key: string]: {
      [key: string]: string;
    };
  };
  dataModel: {
    [key: string]: {
      [key: string]: string;
    };
  };
  features: string[];
}

interface FileStructure {
  [key: string]: {
    file?: { contents: string };
    directory?: FileStructure;
  };
}

interface WebContainerFile {
  file: {
    contents: string;
  };
}

interface WebContainerDirectory {
  directory: {
    [key: string]: WebContainerFile | WebContainerDirectory;
  };
}

type WebContainerFileSystem = {
  [key: string]: WebContainerFile | WebContainerDirectory;
};

function SpecDisplay({ spec }: { spec: Spec }) {
  return (
    <div className="bg-black/50 backdrop-blur-xl p-8 rounded-xl border border-zinc-800 space-y-6 shadow-xl">
      <h2 className="text-2xl font-bold bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">{spec.name}</h2>
      <p className="text-zinc-400 leading-relaxed">{spec.description}</p>
      
      <div className="space-y-3">
        <h3 className="text-lg font-semibold text-white">Features</h3>
        <ul className="grid grid-cols-1 gap-2">
          {spec.features.map((feature, index) => (
            <li key={index} className="flex items-center gap-2 text-zinc-300">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              {feature}
            </li>
          ))}
        </ul>
      </div>

      <div className="space-y-3">
        <h3 className="text-lg font-semibold text-white">Frontend Components</h3>
        <ul className="grid grid-cols-1 gap-2">
          {spec.frontend.map((component, index) => (
            <li key={index} className="flex items-center gap-2 text-zinc-300">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
              {component}
            </li>
          ))}
        </ul>
      </div>

      <div className="space-y-3">
        <h3 className="text-lg font-semibold text-white">API Endpoints</h3>
        {Object.entries(spec.api).map(([endpoint, methods]) => (
          <div key={endpoint} className="pl-4 space-y-2">
            <p className="font-mono text-zinc-200 bg-black/30 px-3 py-1.5 rounded-lg inline-block">{endpoint}</p>
            <ul className="space-y-2">
              {Object.entries(methods).map(([method, description]) => (
                <li key={method} className="flex items-start gap-2 text-zinc-300">
                  <span className="font-mono text-emerald-400 bg-emerald-950/50 px-2 py-0.5 rounded text-sm">{method}</span>
                  <span>{description}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        <h3 className="text-lg font-semibold text-white">Data Models</h3>
        {Object.entries(spec.dataModel).map(([model, fields]) => (
          <div key={model} className="pl-4 space-y-2">
            <p className="font-mono text-zinc-200 bg-black/30 px-3 py-1.5 rounded-lg inline-block">{model}</p>
            <ul className="space-y-2">
              {Object.entries(fields).map(([field, type]) => (
                <li key={field} className="flex items-center gap-2 text-zinc-300">
                  <span className="font-mono text-blue-400 bg-blue-950/50 px-2 py-0.5 rounded text-sm">{field}</span>
                  <span>{type}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

function FileViewer({ selectedFile, fileContent }: { selectedFile: string | null; fileContent: string | null }) {
  if (!selectedFile || !fileContent) {
    return (
      <div className="text-zinc-500 text-center mt-8 p-8 border border-dashed border-zinc-800 rounded-xl">
        Select a file to view its contents
      </div>
    );
  }

  const language = selectedFile.endsWith('.ts') ? 'typescript' :
                  selectedFile.endsWith('.tsx') ? 'typescript' :
                  selectedFile.endsWith('.json') ? 'json' :
                  selectedFile.endsWith('.css') ? 'css' : 'plaintext';

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-zinc-100 font-medium bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">{selectedFile}</h3>
      </div>
      <div className="rounded-xl overflow-hidden border border-zinc-800 shadow-2xl">
        <SyntaxHighlighter
          language={language}
          style={vs2015}
          customStyle={{
            margin: 0,
            padding: '1.5rem',
            borderRadius: '0.75rem',
            fontSize: '0.9rem',
            background: 'rgba(0, 0, 0, 0.5)',
          }}
          showLineNumbers
          wrapLines
          wrapLongLines
        >
          {fileContent}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

const convertToWebContainerFS = (structure: FileStructure): WebContainerFileSystem => {
  const result: WebContainerFileSystem = {};
  
  for (const [name, content] of Object.entries(structure)) {
    if (content.file) {
      result[name] = {
        file: {
          contents: content.file.contents
        }
      };
    } else if (content.directory) {
      result[name] = {
        directory: convertToWebContainerFS(content.directory)
      };
    }
  }
  
  return result;
};

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [spec, setSpec] = useState<Spec | null>(null);
  const [files, setFiles] = useState<FileStructure | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const webcontainerInstance = useRef<WebContainer | null>(null);
  const [showDevEnv, setShowDevEnv] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);

  const handlePromptSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      // First, get the spec
      const specResponse = await fetch('/api/spec', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      });
      const specData = await specResponse.json();
      setSpec(specData);

      // Then, generate the code based on the spec
      const codeResponse = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spec: specData })
      });
      const generatedFiles = await codeResponse.json();
      setFiles(generatedFiles);
    } catch (error) {
      setError('Failed to process prompt. Please try again.');
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const initializeWebContainer = async () => {
    if (!files) return;
    
    setLoading(true);
    setError(null);
    try {
      if (!webcontainerInstance.current) {
        webcontainerInstance.current = await WebContainer.boot();
      }
      const webContainerFiles = convertToWebContainerFS(files);
      await webcontainerInstance.current.mount(webContainerFiles);
      setShowDevEnv(true);
    } catch (error) {
      setError('Failed to initialize development environment. Please try again.');
      console.error('Error initializing WebContainer:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderFileTree = (structure: FileStructure, path: string = '') => {
    return (
      <ul className="pl-4">
        {Object.entries(structure).map(([name, content]) => {
          const fullPath = path ? `${path}/${name}` : name;
          if (content.directory) {
            return (
              <li key={fullPath} className="text-zinc-300">
                <div className="flex items-center gap-1 py-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                  <span className="font-medium">{name}</span>
                </div>
                {renderFileTree(content.directory, fullPath)}
              </li>
            );
          } else {
            return (
              <li key={fullPath}>
                <button
                  className={`flex items-center gap-1 py-1 hover:text-zinc-100 transition-colors ${
                    selectedFile === fullPath ? 'text-zinc-100' : 'text-zinc-400'
                  }`}
                  onClick={() => {
                    setSelectedFile(fullPath);
                    setFileContent(content.file?.contents || '');
                  }}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="font-mono text-sm">{name}</span>
                </button>
              </li>
            );
          }
        })}
      </ul>
    );
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-black via-zinc-900 to-black p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        <h1 className="text-4xl font-bold text-center bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
          AgentOS
        </h1>
        
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl backdrop-blur-xl">
            {error}
          </div>
        )}
        
        {!spec && (
          <div className="max-w-2xl mx-auto space-y-4">
            <textarea 
              className="w-full h-32 bg-black/50 backdrop-blur-xl text-zinc-100 rounded-xl border border-zinc-800 p-6 focus:outline-none focus:ring-2 focus:ring-zinc-700 resize-none shadow-xl"
              placeholder="Enter your prompt here..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            
            <button 
              className="w-full bg-gradient-to-r from-zinc-800 to-zinc-900 hover:from-zinc-700 hover:to-zinc-800 text-white font-medium py-3 px-6 rounded-xl transition-all duration-200 shadow-lg border border-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={handlePromptSubmit}
              disabled={loading || !prompt.trim()}
            >
              {loading ? 'Processing...' : 'Generate Application'}
            </button>
          </div>
        )}

        {spec && !showDevEnv && (
          <div className="space-y-6">
            <SpecDisplay spec={spec} />
            
            <button 
              className="w-full bg-gradient-to-r from-zinc-800 to-zinc-900 hover:from-zinc-700 hover:to-zinc-800 text-white font-medium py-3 px-6 rounded-xl transition-all duration-200 shadow-lg border border-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={initializeWebContainer}
              disabled={loading || !files}
            >
              {loading ? 'Initializing Development Environment...' : 'View Generated Code'}
            </button>
          </div>
        )}

        {showDevEnv && files && (
          <div className="grid grid-cols-[300px_1fr] gap-6 bg-black/50 backdrop-blur-xl rounded-xl border border-zinc-800 p-6 h-[700px] shadow-xl">
            <div className="border-r border-zinc-800 pr-4 overflow-y-auto">
              <h3 className="text-lg font-semibold bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent mb-4">Project Files</h3>
              {renderFileTree(files)}
            </div>
            <div className="overflow-y-auto">
              <FileViewer selectedFile={selectedFile} fileContent={fileContent} />
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
