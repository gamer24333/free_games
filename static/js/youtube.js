document.addEventListener('DOMContentLoaded', () => {
    const searchBar = document.getElementById('searchBar');
    const videoCards = document.querySelectorAll('.video-card');
    const noResultsMessage = document.getElementById('noResultsMessage');

    searchBar.addEventListener('keyup', (e) => {
        const searchString = e.target.value.toLowerCase().strip();
        let hasResults = false;

        videoCards.forEach((card) => {
            // Holt den Titel und die Kategorie aus den HTML-Attributen
            const title = card.getAttribute('data-title');
            const category = card.getAttribute('data-category');

            // Prüft, ob der Suchbegriff im Titel oder in der Kategorie vorkommt
            if (title.includes(searchString) || category.includes(searchString)) {
                card.style.display = 'block'; // Video anzeigen
                hasResults = true;
            } else {
                card.style.display = 'none';  // Video verstecken
            }
        });

        // Wenn kein einziges Video passt, zeige die Fehlermeldung
        if (hasResults) {
            noResultsMessage.style.display = 'none';
        } else {
            noResultsMessage.style.display = 'block';
        }
    });
});
