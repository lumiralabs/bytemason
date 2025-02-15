// Task Item Component
const TaskItem = ({ task }) => {
    return <li className="border-b p-2">{task.name}</li>;
};

export default TaskItem;
