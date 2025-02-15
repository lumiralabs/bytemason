// API Routes
import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function POST(request: Request) {
    const { taskData } = await request.json();
    const { data, error } = await supabase.from('tasks').insert(taskData);
    if (error) return NextResponse.json({ error: error.message }, { status: 400 });
    return NextResponse.json(data, { status: 201 });
}

export async function DELETE(request: Request) {
    const { id } = request.query;
    const { error } = await supabase.from('tasks').delete().eq('id', id);
    if (error) return NextResponse.json({ error: error.message }, { status: 400 });
    return NextResponse.json({ message: 'Task deleted' }, { status: 200 });
}
