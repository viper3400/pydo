/**
 * PyTodo JavaScript
 * Client-side interactivity for the todo app
 */

const PENDING_EDIT_INDEX_KEY = 'pytodo_pending_edit_index';
let switchModal = null;
let switchSourceTodoItem = null;
let switchTargetTodoItem = null;

function getEditForm(todoItem) {
    return todoItem?.querySelector('.edit-form') || null;
}

function getEditInput(todoItem) {
    return todoItem?.querySelector('.edit-input') || null;
}

function getPrioritySelect(todoItem) {
    return todoItem?.querySelector('select[name="priority"]') || null;
}

function getTodoIndex(todoItem) {
    return todoItem?.dataset?.index || '';
}

function setPendingEditIndex(index) {
    try {
        if (index) {
            sessionStorage.setItem(PENDING_EDIT_INDEX_KEY, index);
        } else {
            sessionStorage.removeItem(PENDING_EDIT_INDEX_KEY);
        }
    } catch (error) {
        // Ignore storage errors (private mode/quota issues).
    }
}

function getPendingEditIndex() {
    try {
        return sessionStorage.getItem(PENDING_EDIT_INDEX_KEY) || '';
    } catch (error) {
        return '';
    }
}

function showEditMode(todoItem, focusInput = false) {
    const editForm = getEditForm(todoItem);
    const todoText = todoItem?.querySelector('.todo-text');
    if (!editForm || !todoText) {
        return;
    }

    const editInput = getEditInput(todoItem);
    const prioritySelect = getPrioritySelect(todoItem);
    if (editInput && !editForm.dataset.originalText) {
        editForm.dataset.originalText = editInput.value;
    }
    if (prioritySelect && editForm.dataset.originalPriority === undefined) {
        editForm.dataset.originalPriority = prioritySelect.value;
    }

    todoText.classList.add('d-none');
    editForm.classList.remove('d-none');

    if (focusInput) {
        editInput?.focus();
    }
}

function hideEditMode(todoItem) {
    const editForm = getEditForm(todoItem);
    const todoText = todoItem?.querySelector('.todo-text');
    if (!editForm || !todoText) {
        return;
    }

    todoText.classList.remove('d-none');
    editForm.classList.add('d-none');
}

function hasUnsavedEditChanges(todoItem) {
    const editForm = getEditForm(todoItem);
    const editInput = getEditInput(todoItem);
    const prioritySelect = getPrioritySelect(todoItem);
    if (!editForm || !editInput) {
        return false;
    }

    const originalText = editForm.dataset.originalText ?? '';
    const originalPriority = editForm.dataset.originalPriority ?? '';
    const currentText = editInput.value;
    const currentPriority = prioritySelect ? prioritySelect.value : '';

    return currentText !== originalText || currentPriority !== originalPriority;
}

function resetEditFormToOriginal(todoItem) {
    const editForm = getEditForm(todoItem);
    const editInput = getEditInput(todoItem);
    const prioritySelect = getPrioritySelect(todoItem);
    if (!editForm || !editInput) {
        return;
    }

    editInput.value = editForm.dataset.originalText ?? editInput.defaultValue;
    if (prioritySelect) {
        prioritySelect.value = editForm.dataset.originalPriority ?? prioritySelect.defaultValue;
    }
}

function getActiveEditForm() {
    return document.querySelector('.edit-form:not(.d-none)');
}

function getActiveTodoItem() {
    return getActiveEditForm()?.closest('.todo-item') || null;
}

function isSwitchModalOpen() {
    const modalEl = document.getElementById('editSwitchModal');
    return !!modalEl && modalEl.classList.contains('show');
}

function escapeHtml(value) {
    return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function getChangedRange(originalValue, currentValue) {
    let start = 0;
    const original = String(originalValue);
    const current = String(currentValue);

    while (start < original.length && start < current.length && original[start] === current[start]) {
        start += 1;
    }

    let originalEnd = original.length;
    let currentEnd = current.length;
    while (originalEnd > start && currentEnd > start && original[originalEnd - 1] === current[currentEnd - 1]) {
        originalEnd -= 1;
        currentEnd -= 1;
    }

    return { start, originalEnd, currentEnd };
}

function renderChangedOnlyHtml(text, start, end) {
    const value = String(text);
    const before = escapeHtml(value.slice(0, start));
    const changed = escapeHtml(value.slice(start, end));
    const after = escapeHtml(value.slice(end));

    if (!changed) {
        return `${before}${after}`;
    }
    return `${before}<mark>${changed}</mark>${after}`;
}

function populateSwitchModal(currentTodoItem) {
    const entryTextElement = document.getElementById('editSwitchEntryText');
    const textSummaryElement = document.getElementById('editSwitchTextChangeSummary');
    const prioritySummaryElement = document.getElementById('editSwitchPriorityChangeSummary');
    const editForm = getEditForm(currentTodoItem);
    const editInput = getEditInput(currentTodoItem);
    const prioritySelect = getPrioritySelect(currentTodoItem);

    const entryText = currentTodoItem?.querySelector('.task-text')?.textContent?.trim() || 'this task';
    const originalText = editForm?.dataset.originalText ?? '';
    const currentText = editInput?.value ?? '';
    const originalPriority = editForm?.dataset.originalPriority ?? '';
    const currentPriority = prioritySelect?.value ?? '';
    const textChanged = originalText !== currentText;
    const priorityChanged = originalPriority !== currentPriority;

    if (entryTextElement) {
        entryTextElement.textContent = entryText;
    }
    if (textSummaryElement) {
        if (!textChanged) {
            textSummaryElement.innerHTML = `
                <div class="mb-1"><span class="text-muted">From:</span> ${escapeHtml(originalText || '(empty)')}</div>
                <div><span class="text-muted">To:</span> ${escapeHtml(currentText || '(empty)')}</div>
            `;
        } else {
            const range = getChangedRange(originalText, currentText);
            textSummaryElement.innerHTML = `
                <div class="mb-1"><span class="text-muted">From:</span> ${renderChangedOnlyHtml(originalText || '(empty)', range.start, range.originalEnd)}</div>
                <div><span class="text-muted">To:</span> ${renderChangedOnlyHtml(currentText || '(empty)', range.start, range.currentEnd)}</div>
            `;
        }
    }
    if (prioritySummaryElement) {
        const fromLabel = originalPriority || 'No Prio';
        const toLabel = currentPriority || 'No Prio';
        const changedBadge = priorityChanged
            ? ' <span class="badge bg-warning text-dark">changed</span>'
            : '';
        const toValueHtml = priorityChanged ? `<mark>${escapeHtml(toLabel)}</mark>` : escapeHtml(toLabel);

        prioritySummaryElement.innerHTML = `
            <div class="mb-1"><span class="text-muted">From:</span> ${escapeHtml(fromLabel)}</div>
            <div><span class="text-muted">To:</span> ${toValueHtml}${changedBadge}</div>
        `;
    }
}

function showSwitchModal(currentTodoItem, nextTodoItem) {
    if (!switchModal) {
        return;
    }

    populateSwitchModal(currentTodoItem);

    switchSourceTodoItem = currentTodoItem;
    switchTargetTodoItem = nextTodoItem;
    switchModal.show();
}

// Edit task functionality
function editTask(element, event) {
    event.stopPropagation();

    const todoItem = element.closest('.todo-item');
    const editForm = getEditForm(todoItem);

    if (todoItem.classList.contains('completed')) {
        return; // Don't allow editing completed tasks
    }

    if (editForm && !editForm.classList.contains('d-none')) {
        return; // Already in edit mode
    }

    const activeTodoItem = getActiveTodoItem();
    if (activeTodoItem && activeTodoItem !== todoItem) {
        if (hasUnsavedEditChanges(activeTodoItem)) {
            showSwitchModal(activeTodoItem, todoItem);
            return;
        }
        hideEditMode(activeTodoItem);
        showEditMode(todoItem, true);
        return;
    }

    // Hide text, show form
    showEditMode(todoItem, true);
}

function cancelEdit(button) {
    const todoItem = button.closest('.todo-item');
    resetEditFormToOriginal(todoItem);
    hideEditMode(todoItem);
    setPendingEditIndex('');
}

document.addEventListener('DOMContentLoaded', function() {
    const switchModalEl = document.getElementById('editSwitchModal');
    if (switchModalEl && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        switchModal = new bootstrap.Modal(switchModalEl);

        switchModalEl.addEventListener('hidden.bs.modal', function() {
            switchSourceTodoItem = null;
            switchTargetTodoItem = null;
        });
    }

    const switchSaveBtn = document.getElementById('editSwitchSaveBtn');
    if (switchSaveBtn) {
        switchSaveBtn.addEventListener('click', function() {
            if (!switchSourceTodoItem || !switchTargetTodoItem) {
                return;
            }
            const currentEditForm = switchSourceTodoItem.querySelector('.edit-form');
            if (!currentEditForm) {
                return;
            }

            const nextIndex = getTodoIndex(switchTargetTodoItem);
            setPendingEditIndex(nextIndex);
            switchModal?.hide();
            currentEditForm.requestSubmit();
        });
    }

    const switchCancelBtn = document.getElementById('editSwitchCancelBtn');
    if (switchCancelBtn) {
        switchCancelBtn.addEventListener('click', function() {
            if (!switchSourceTodoItem || !switchTargetTodoItem) {
                return;
            }
            resetEditFormToOriginal(switchSourceTodoItem);
            hideEditMode(switchSourceTodoItem);
            showEditMode(switchTargetTodoItem, true);
            setPendingEditIndex('');
            switchModal?.hide();
        });
    }

    // If user chose "Save" while switching rows, reopen target row after reload.
    const pendingIndex = getPendingEditIndex();
    if (pendingIndex) {
        const todoItem = document.querySelector(`.todo-item[data-index="${pendingIndex}"]`);
        if (todoItem && !todoItem.classList.contains('completed')) {
            showEditMode(todoItem, true);
        }
        setPendingEditIndex('');
    }

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
            if (isSwitchModalOpen()) {
                return;
            }
            const editForm = getActiveEditForm();
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
