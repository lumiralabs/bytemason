// Supabase Client
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export const fetchUserTasks = async () => {
    // Fetch tasks for the authenticated user
    const { data, error } = await supabase.from('tasks').select().eq('user_id', supabase.auth.user()?.id);
    if (error) throw error;
    return data;
};

export const fetchUserSettings = async () => {
    // Fetch user settings
    // Implementation here...
};
