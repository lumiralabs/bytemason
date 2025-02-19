# Best practices for Next.js 14 development

STRICTLY FOLLOW THESE GUIDELINES. DO NOT USE ANY OTHER OLD PATTERNS.

## Project Structure

Use the App Router pattern instead of the Pages Router for better organization and features:

- Place all routes under `app/` directory instead of `pages/`
- Create route segments using folders (e.g. `app/dashboard/settings/`)
- Use `page.tsx` files to make routes publicly accessible
- Use `layout.tsx` for shared UI between routes
- Place route-specific components in the route folder
- Keep shared components in `components/`
- Use `loading.tsx` for suspense boundaries
- Use `error.tsx` for error handling
- Place API routes under `app/api/`

## Project Structure DOs and DON'Ts

✅ DO:
├── app/
│ ├── (auth)/ # Auth group routes
│ │ ├── login/
│ │ │ └── page.tsx
│ │ └── register/
│ │ └── page.tsx
│ ├── dashboard/ # Dashboard routes
│ │ ├── page.tsx
│ │ ├── layout.tsx
│ │ └── settings/
│ │ └── page.tsx
│ ├── api/ # API routes
│ │ └── users/
│ │ └── route.ts
│ ├── layout.tsx # Root layout
│ └── page.tsx # Home page
└── components/ # Shared components
├── Button.tsx
└── Header.tsx

❌ DON'T:
└── pages/ # Don't use Pages Router
├── \_app.tsx
├── index.tsx
├── login.tsx
├── api/
│ └── users.ts
└── components/ # Don't mix components with pages
├── Button.tsx
└── Header.tsx

## KEY POINTS TO ALWAYS FOLLOW

- Always use the most latest nextJS 14 app router conventions in all cases, weather imports and exports,folder structure, api structure, etc.
- Always remember that you are working in a monorepo and that you can use the libs and types in any file you want.
- Always remember to add "use client" at top of all the client side components. any dynamic imports should be in the client side components.
- Always use the tailwind css for styling.
- Use shadcn to add components rather than creating new ones. put them in `components/ui` folder.
- Try to use the existing components where possible for the ui and avoid creating duplicate ones. 
- Don't add duplicate or very similar code, follow the DRY principle.

## 1. List of Existing Files and Their Purposes

- **Root Files:**
  - `config.ts`: Likely contains configuration settings for the application.
  - `middleware.ts`: Contains middleware logic, possibly for handling requests or authentication.
  - `next-env.d.ts`: TypeScript environment definitions for Next.js.
  - `next.config.js`: Configuration file for Next.js, used to customize the build process.
  - `postcss.config.js`: Configuration for PostCSS, a tool for transforming CSS.
  - `tailwind.config.js`: Configuration for Tailwind CSS, a utility-first CSS framework.
- **Components Directory:**
  - `components/ButtonAccount.tsx`: A React component, likely a button related to user account actions.
  - `components/ButtonSignin.tsx`: A React component, likely a button for signing in.
  - `components/LayoutClient.tsx`: A React component, possibly defining the layout for client-side pages.
- **Libs Directory:**
  - `libs/api.ts`: Contains API-related logic or functions.
  - `libs/seo.tsx`: Contains SEO-related components or logic.
- **Types Directory:**
  - `types/config.ts`: Type definitions related to configuration.
  - `types/index.ts`: Central export file for types.
  - `types/next-auth.d.ts`: Type definitions related to authentication, possibly using NextAuth.js.
- **App Directory:**
  - `app/layout.tsx`: Defines the layout for the application, likely used by Next.js.
  - `app/page.tsx`: The main page component for the application.
- **Lib Directory:**
  - `libs/utils.ts`: Utility functions used across the application.


 currently installed packages:
 ```json
 {
  "name": "",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "postbuild": "next-sitemap",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "@headlessui/react": "^1.7.18",
    "@mdx-js/loader": "^2.3.0",
    "@mdx-js/react": "^2.3.0",
    "@radix-ui/react-icons": "^1.3.0",
    "@radix-ui/react-slot": "^1.1.0",
    "@supabase/ssr": "^0.4.0",
    "@supabase/supabase-js": "^2.45.0",
    "axios": "^1.6.8",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "eslint": "8.47.0",
    "eslint-config-next": "13.4.19",
    "form-data": "^4.0.0",
    "framer-motion": "^11.11.9",
    "lucide-react": "^0.453.0",
    "next": "^14.1.4",
    "nextjs-toploader": "^1.6.11",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "react-hot-toast": "^2.4.1",
    "react-syntax-highlighter": "^15.5.0",
    "react-tooltip": "^5.26.3",
    "tailwind-merge": "^2.5.4",
    "tailwindcss-animate": "^1.0.7",
    "zod": "^3.22.4"
  },
  "devDependencies": {
    "@types/axios": "^0.9.36",
    "@types/jest": "^29.5.12",
    "@types/node": "^20.12.2",
    "@types/react": "^18.2.73",
    "@types/react-dom": "^18.2.23",
    "@types/react-syntax-highlighter": "^15.5.11",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.3",
    "typescript": "^5.4.3"
  }
}
```



### 2. Component Patterns and Their Usage

The components are organized in a `components` directory, with specific components like buttons and layout components. This suggests a pattern of reusable UI components, which is common in React applications to promote reusability and maintainability.

### 3. Current Routing Implementation

The `app` directory structure suggests the use of Next.js 14 App Router, where each subdirectory or file represents a route. For example, `app/dashboard` and `app/signin` likely correspond to `/dashboard` and `/signin` routes, respectively.

For all the api calls use this premade wrapper because it automatically handles the error handling and redirects to the login page if the user is not authenticated.

```Typescript
// libs/api.ts

import axios from "axios";
import { toast } from "react-hot-toast";
import { redirect } from "next/navigation";
import config from "@/config";

// use this to interact with our own API (/app/api folder) from the front-end side
const apiClient = axios.create({
  baseURL: "/api",
});

apiClient.interceptors.response.use(
  function (response: any) {
    return response.data;
  },
  function (error: any) {
    let message = "";

    if (error.response?.status === 401) {
      // User not auth, ask to re login
      toast.error("Please login");
      // Sends the user to the login page
      redirect(config.auth.loginUrl);
      } else {
      message =
        error?.response?.data?.error || error.message || error.toString();
    }

    error.message =
      typeof message === "string" ? message : JSON.stringify(message);

    console.error(error.message);

    // Automatically display errors to the user
    if (error.message) {
      toast.error(error.message);
    } else {
      toast.error("something went wrong...");
    }
    return Promise.reject(error);
  }
);

export default apiClient;

```

### 4. Authentication Setup

The `libs/supabase` subdirectory contains all the inititalizations and middleware like for client and server.
 - user details can be taken care by just these commands
 ```typescript
 import { createClient } from "@/libs/supabase/server";
 const supabase = createClient();
 const {  data: { user } } = await supabase.auth.getUser();
 ```
- Dont write your own middleware or any auth logic, everything is already premade in the `libs/supabase` folder. 
- A register + login page is already made which user supabse magic link and google oauth, magiclink works by default so dont worry about any auth management, just make sure to redirect to /signin page if the user is not authenticated. You dont need to make any changes to this page.

```typescript
// app/signin/page.tsx

"use client";

import Link from "next/link";
import { useState } from "react";
import { createClient } from "@/libs/supabase/client";
import { Provider } from "@supabase/supabase-js";
import toast from "react-hot-toast";
import config from "@/config";

// This a login/singup page for Supabase Auth.
// Successfull login redirects to /api/auth/callback where the Code Exchange is processed (see app/api/auth/callback/route.js).
export default function Login() {
  const supabase = createClient();
  const [email, setEmail] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isDisabled, setIsDisabled] = useState<boolean>(false);

  const handleSignup = async (
    e: any,
    options: {
      type: string;
      provider?: Provider;
    }
  ) => {
    e?.preventDefault();

    setIsLoading(true);

    try {
      const { type, provider } = options;
      const redirectURL = window.location.origin + "/api/auth/callback";

      if (type === "oauth") {
        await supabase.auth.signInWithOAuth({
          provider,
          options: {
            redirectTo: redirectURL,
          },
        });
      } else if (type === "magic_link") {
        await supabase.auth.signInWithOtp({
          email,
          options: {
            emailRedirectTo: redirectURL,
          },
        });

        toast.success("Check your emails!");

        setIsDisabled(true);
      }
    } catch (error) {
      console.log(error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="p-8 md:p-24">
      <div className="text-center mb-4">
        <Link href="/" className="btn btn-ghost btn-sm">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-5 h-5"
          >
            <path
              fillRule="evenodd"
              d="M15"
              clipRule="evenodd"
            />
          </svg>
          Home
        </Link>
      </div>
      <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-center mb-12">
        Sign-in to {config.appName}{" "}
      </h1>

      <div className="space-y-8 max-w-xl mx-auto">
        <button
          className="btn btn-block"
          onClick={(e) =>
            handleSignup(e, { type: "oauth", provider: "google" })
          }
          disabled={isLoading}
        >
          {isLoading ? (
            <span className="loading loading-spinner loading-xs"></span>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="w-6 h-6"
              viewBox="0 0 48 48"
            >
          )}
          Sign-up with Google
        </button>

        <div className="divider text-xs text-base-content/50 font-medium">
          OR
        </div>

        <form
          className="form-control w-full space-y-4"
          onSubmit={(e) => handleSignup(e, { type: "magic_link" })}
        >
          <input
            required
            type="email"
            value={email}
            autoComplete="email"
            placeholder="tom@cruise.com"
            className="input input-bordered w-full placeholder:opacity-60"
            onChange={(e) => setEmail(e.target.value)}
          />

          <button
            className="btn btn-primary btn-block"
            disabled={isLoading || isDisabled}
            type="submit"
          >
            {isLoading && (
              <span className="loading loading-spinner loading-xs"></span>
            )}
            Send Magic Link
          </button>
        </form>
      </div>
    </main>
  );
}
```

Always use the most latest nextJS 14 app router conventions in all cases, weather imports and exports,folder structure, api structure, etc.
