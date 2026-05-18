document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadSection = document.getElementById('upload-section');
    const loading = document.getElementById('loading');
    const errorMessage = document.getElementById('error-message');
    const resultSection = document.getElementById('result-section');
    const summaryBody = document.getElementById('summary-body');
    const totalRowsSpan = document.getElementById('total-rows');
    const resetBtn = document.getElementById('reset-btn');
    const btnSummen = document.getElementById('btn-summen');
    const btnEinzel = document.getElementById('btn-einzel');

    // Drag and drop events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    // Handle clicked files
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    // Reset UI
    resetBtn.addEventListener('click', () => {
        resultSection.classList.add('hidden');
        uploadSection.classList.remove('hidden');
        dropZone.classList.remove('hidden');
        errorMessage.classList.add('hidden');
        fileInput.value = '';
    });

    function handleFiles(files) {
        if (files.length === 0) return;
        
        // Basic validation
        let validFiles = [];
        for (let i = 0; i < files.length; i++) {
            if (files[i].name.toLowerCase().endsWith('.csv')) {
                validFiles.push(files[i]);
            }
        }
        
        if (validFiles.length === 0) {
            showError("Bitte lade nur CSV-Dateien hoch.");
            return;
        }

        uploadFile(validFiles);
    }

    function uploadFile(files) {
        // UI states
        dropZone.classList.add('hidden');
        errorMessage.classList.add('hidden');
        loading.classList.remove('hidden');

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('file', files[i]);
        }

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loading.classList.add('hidden');
            
            if (data.error) {
                showError(data.error);
                dropZone.classList.remove('hidden');
                return;
            }

            // Success! Render results
            renderResults(data);
        })
        .catch(error => {
            loading.classList.add('hidden');
            dropZone.classList.remove('hidden');
            showError("Netzwerkfehler: " + error.message);
        });
    }

    function renderResults(data) {
        uploadSection.classList.add('hidden');
        resultSection.classList.remove('hidden');
        
        totalRowsSpan.textContent = data.total_rows;
        
        // Render table rows
        summaryBody.innerHTML = '';
        data.summary.forEach(row => {
            const tr = document.createElement('tr');
            
            // Highlight Ungeklärt if it has a value other than 0
            if (row.kategorie === 'Ungeklärt' && row.summe_eur !== 0) {
                tr.classList.add('row-ungeklaert');
            }
            
            tr.innerHTML = `
                <td>${row.kategorie}</td>
                <td class="text-right">${row.summe_formatiert}</td>
            `;
            summaryBody.appendChild(tr);
        });
        
        // Setup downloads
        // Wir benötigen ein BOM (Byte Order Mark), damit Excel UTF-8 korrekt erkennt
        const bom = new Uint8Array([0xEF, 0xBB, 0xBF]);
        
        const blobSummen = new Blob([bom, data.csv_summen], { type: 'text/csv;charset=utf-8;' });
        const blobEinzel = new Blob([bom, data.csv_kontrolle], { type: 'text/csv;charset=utf-8;' });
        
        if (btnSummen.href) URL.revokeObjectURL(btnSummen.href);
        if (btnEinzel.href) URL.revokeObjectURL(btnEinzel.href);
        
        btnSummen.href = URL.createObjectURL(blobSummen);
        btnSummen.download = 'kibiz_summen_abgabebereit.csv';
        
        btnEinzel.href = URL.createObjectURL(blobEinzel);
        btnEinzel.download = 'kibiz_einzelbuchungen_kontrolle.csv';
    }

    function showError(msg) {
        errorMessage.textContent = msg;
        errorMessage.classList.remove('hidden');
    }
});
