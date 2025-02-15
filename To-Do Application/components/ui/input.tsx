// Input Component
const Input = ({ value, onChange, placeholder }) => {
    return (
        <input
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            className="border rounded p-2 mb-4"
        />
    );
};

export default Input;
