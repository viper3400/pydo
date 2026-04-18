/**
 * PyTodo JavaScript
 * Client-side interactivity for the todo app
 */

// Edit task functionality
function editTask(element, event) {
    event.stopPropagation();

    const todoItem = element.closest('.todo-item');
    const editForm = todoItem.querySelector('.edit-form');
    const todoText = todoItem.querySelector('.todo-text');

    if (todoItem.classList.contains('completed')) {
        return; // Don't allow editing completed tasks
    }

    if (editForm && !editForm.classList.contains('d-none')) {
        return; // Already in edit mode
    }

    // Hide text, show form
    todoText.classList.add('d-none');
    editForm?.classList.remove('d-none');
    editForm?.querySelector('.edit-input')?.focus();
}

function cancelEdit(button) {
    const todoItem = button.closest('.todo-item');
    const editForm = todoItem.querySelector('.edit-form');
    const todoText = todoItem.querySelector('.todo-text');

    // Show text, hide form
    todoText.classList.remove('d-none');
    editForm.classList.add('d-none');
}

document.addEventListener('DOMContentLoaded', function() {
    // Add form submission handler
    const addForm = document.querySelector('form[action*="/add"]');
    if (addForm) {
        addForm.addEventListener('submit', function(e) {
            const textInput = this.querySelector('input[name="text"]');
            if (!textInput.value.trim()) {
                e.preventDefault();
                return false;
            }
        });
    }

    // Delete confirmation
    const deleteForms = document.querySelectorAll('.delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to delete this task?')) {
                e.preventDefault();
            }
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K to focus add todo input
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const input = document.querySelector('input[name="text"]');
            if (input) input.focus();
        }

        // Escape to cancel edit
        if (e.key === 'Escape') {
            const editForm = document.querySelector('.edit-form:not(.d-none)');
            if (editForm) {
                cancelEdit(editForm.querySelector('button[type="button"]'));
            }
        }
    });

    // Animate checkbox changes
    const checkboxes = document.querySelectorAll('.todo-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const item = this.closest('.todo-item');
            if (item) {
                item.style.opacity = '0.5';
            }
        });
    });

    // Edit form submission
    const editForms = document.querySelectorAll('.edit-form');
    editForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const input = this.querySelector('.edit-input');
            if (!input.value.trim()) {
                e.preventDefault();
                alert('Task text cannot be empty');
                return false;
            }
        });
    });
});

// Helper function for AJAX requests (future use)
function makeRequest(method, url, data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest'
        }
    };

    if (data) {
        options.body = new URLSearchParams(data);
    }

    return fetch(url, options)
        .then(response => response.json())
        .catch(error => console.error('Error:', error));
}
