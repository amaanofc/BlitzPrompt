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
        alert('Please login to favorite prompts!');
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
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error toggling favorite status. Please try again.');
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
        alert('Please login to publish prompts!');
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
            alert('Your prompt has been published to the library successfully!');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error publishing prompt. Please try again.');
        btn.innerHTML = originalContent;
        btn.disabled = false;
    });
}