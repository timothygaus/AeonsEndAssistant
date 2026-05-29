interface ButtonProps {
    onClick: () => void
    children: React.ReactNode
    variant?: 'primary' | 'danger'
    disabled?: boolean
}

function Button({ onClick, children, variant = 'primary', disabled = false }: ButtonProps) {
    const styles = {
        primary: 'px-6 py-3 bg-blue-600 rounded font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:bg-gray-500 disabled:cursor-not-allowed',
        danger: 'px-6 py-3 bg-red-600 rounded font-semibold hover:bg-red-700 disabled:opacity-50 disabled:bg-gray-500 disabled:cursor-not-allowed'
    }
    return (
        <button onClick={onClick} className={styles[variant]} disabled={disabled}>
            {children}
        </button>
    )
}

export default Button