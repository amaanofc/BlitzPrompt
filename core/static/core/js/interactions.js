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
    if (!isAuthenticated) {  // Will be set in template
        alert('Please login to favorite prompts!');
        return;
    }

    fetch(`/toggle-favorite/${promptId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        }
    })
        .then(response => response.json())
        .then(data => {
            const btn = document.getElementById('favoriteBtn');
            btn.textContent = data.is_favorited ? '★ Unfavorite' : '☆ Favorite';
        })
        .catch(error => console.error('Error:', error));
}

function publishPrompt(promptId) {
    if (!isAuthenticated) {
        alert('Please login to publish prompts!');
        return;
    }

    fetch(`/publish-prompt/${promptId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.published) alert('Published successfully!');
        })
        .catch(error => console.error('Error:', error));
}