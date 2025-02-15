// Task Form Component
import { useState } from 'react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { supabase } from '@/lib/supabase';

const TaskForm = () => {
    const [taskName, setTaskName] = useState('');
    // handle form submission
    const handleSubmit = async (e) => {
        e.preventDefault();
        await supabase.from('tasks').insert({ name: taskName });
        setTaskName('');
    };

    return (
        <form onSubmit={handleSubmit} className="flex flex-col mb-4">
            <Input
                value={taskName}
                onChange={(e) => setTaskName(e.target.value)}
                placeholder="Add a new task"
            />
            <Button type="submit">Add Task</Button>
        </form>
    );
};

export default TaskForm;
