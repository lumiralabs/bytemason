// Task List Component
import TaskItem from './TaskItem';

const TaskList = ({ tasks }) => {
    return (
        <ul className="w-full">
            {tasks.map((task) => <TaskItem key={task.id} task={task} />)}
        </ul>
    );
};

export default TaskList;
