# Blueberry

Blueberry is a CLI tool that builds your app with the help of AI agents.

Read the docs [here](https://lumiralabs.github.io/blueberry/).

## Installation

To install blueberry locally for development:

```bash
uv pip install -e .
```

## Usage

Follow these commands in sequence:

### 1. Create a new project

```bash
berry new "name of your idea in a word"
```
This creates a directory and initializes the project skeleton with necessary configuration files.

### 2. Navigate to project directory

```bash
cd <dir that was created>
```

### 3. Generate specification

```bash
berry plan "prompt about your app"
```
This creates a detailed specification file for your app inside the spec directory. The more specific your prompt, the better the generated specification will be.

### 4. Set up database (can be done later)

```bash
berry db setup <spec_file_path>
```
This takes your Supabase credentials and initializes Supabase, generating migrations. This step can be performed after code generation, doing it in this order improves the accuracy of the generated code.

### 5. Push database changes

```bash
berry db push
```
This pushes the migrations to your Supabase project. This step is required to make your database schema available for your application.

### 6. Generate code

```bash
berry code <spec_file_path>
```
This starts code generation, downloads UI components if necessary, and fixes compile-time errors using the repair agent. After generation completes, you can run `npm run dev` to start your application locally.

### 7. Repair code (can be run independently after coede generation)

```bash
berry repair
```
This command can be run independently at any time to fix compile-time errors.

**Note:** The database setup steps (4-5) must be completed at some point for a fully functional application. While you can postpone these steps until after code generation, completing them in the recommended order generally results in more accurate code generation and fewer integration issues.
