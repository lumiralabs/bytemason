// TypeScript Types
export interface Task {
    id: string;
    user_id: string;
    name: string;
    due_date: string;
    priority: number;
    completed: boolean;
    category?: string[];
    tags?: string[];
}

export interface User {
    id: string;
    email: string;
    role: string;
}
