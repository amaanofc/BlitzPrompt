// Initialize with safe defaults
document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('prompt_id').value = '0';

    // Form validation
    document.getElementById('query-form').addEventListener('submit', function (e) {
        const promptId = document.getElementById('prompt_id').value;
        if (!promptId || promptId === '0') {
            e.preventDefault();
            alert('Please select a prompt first!');
        }
    });
});

function setPrompt(promptId) {
    document.getElementById('prompt_id').value = promptId;
    console.log('Prompt selected:', promptId);
}

function toggleFavorite(promptId) {
    if (!window.appConfig || !window.appConfig.isAuthenticated) {
        showNotification('Please login to favorite prompts.', 'warning');
        window.location.href = '/login/';
        return;
    }

    // Visual feedback - disable button during request
    const btn = document.getElementById('favoriteBtn');
    const originalContent = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Processing...';

    fetch(`/toggle-favorite/${promptId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': window.appConfig.csrfToken || document.querySelector('[name=csrfmiddlewaretoken]').value,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Update button text based on response
        btn.textContent = data.is_favorited ? '★ Unfavorite' : '☆ Favorite';
        btn.disabled = false;

        // Update favorites list in the sidebar
        updateFavoritesList(promptId, data.is_favorited);
        
        // Show a subtle notification
        const message = data.is_favorited ? 
            'Added to favorites' : 
            'Removed from favorites';
        showNotification(message, 'success');
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error toggling favorite status.', 'danger');
        btn.textContent = originalContent;
        btn.disabled = false;
    });
}

function updateFavoritesList(promptId, isFavorited) {
    // Find the prompt in the favorites list
    const favoritesList = document.querySelector('.list-group');
    if (!favoritesList) return;

    const existingItem = Array.from(favoritesList.querySelectorAll('.list-group-item')).find(
        item => item.getAttribute('onclick') && item.getAttribute('onclick').includes(`'${promptId}'`)
    );

    if (isFavorited && !existingItem) {
        // Need to add to favorites list - fetch prompt details
        fetch(`/api/prompt/${promptId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const newItem = document.createElement('a');
                    newItem.href = '#';
                    newItem.className = 'list-group-item list-group-item-action';
                    newItem.textContent = data.title;
                    newItem.setAttribute('onclick', `setPrompt('${promptId}', '${data.title}', '${data.content.replace(/'/g, "\\'")}')`);
                    favoritesList.appendChild(newItem);
                }
            })
            .catch(error => console.error('Error fetching prompt details:', error));
    } else if (!isFavorited && existingItem) {
        // Remove from favorites list
        existingItem.remove();
    }
}

function publishPrompt(promptId) {
    if (!window.appConfig || !window.appConfig.isAuthenticated) {
        showNotification('Please login to publish prompts.', 'warning');
        window.location.href = '/login/';
        return;
    }

    // Visual feedback
    const btn = document.querySelector('button[onclick*="publishPrompt"]');
    const originalContent = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Publishing...';

    fetch(`/publish-prompt/${promptId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': window.appConfig.csrfToken || document.querySelector('[name=csrfmiddlewaretoken]').value,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.published) {
            btn.innerHTML = '<i class="fas fa-check me-1"></i> Published';
            btn.classList.remove('btn-info');
            btn.classList.add('btn-success');
            btn.disabled = true;
            showNotification('Your prompt has been published to the library successfully!', 'success');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error publishing prompt.', 'danger');
        btn.innerHTML = originalContent;
        btn.disabled = false;
    });
}

// Helper function to show non-blocking notifications
function showNotification(message, type) {
    // Create notification container if it doesn't exist
    let notificationContainer = document.getElementById('notification-container');
    
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        notificationContainer.style.position = 'fixed';
        notificationContainer.style.top = '10px';
        notificationContainer.style.right = '10px';
        notificationContainer.style.zIndex = '9999';
        notificationContainer.style.maxWidth = '300px';
        document.body.appendChild(notificationContainer);
    }
    
    // Create notification
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification`;
    notification.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            ${message}
            <button type="button" class="btn-close btn-sm" aria-label="Close"></button>
        </div>
    `;
    notification.style.opacity = '0';
    notification.style.transform = 'translateY(-20px)';
    notification.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    
    // Add close button functionality
    const closeBtn = notification.querySelector('.btn-close');
    closeBtn.addEventListener('click', () => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            notification.remove();
        }, 300);
    });
    
    // Add to container
    notificationContainer.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateY(0)';
    }, 10);
    
    // Auto remove after 4 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 4000);
}