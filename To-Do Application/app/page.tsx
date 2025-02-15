// Home Page
import TaskList from '@/components/feature/TaskList';
import TaskForm from '@/components/feature/TaskForm';
import { fetchUserTasks } from '@/lib/supabase';
import { useEffect, useState } from 'react';

const HomePage = () => {
    const [tasks, setTasks] = useState([]);

    useEffect(() => {
        const loadTasks = async () => {
            const userTasks = await fetchUserTasks();
            setTasks(userTasks);
        };
        loadTasks();
    }, []);

    return (
        <div className="flex flex-col items-center">
            <TaskForm />
            <TaskList tasks={tasks} />
        </div>
    );
};

export default HomePage;
