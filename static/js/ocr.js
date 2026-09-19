let originalBoxes = [];
let originalWidth = 3000;
let originalHeight = 2000;

function bringToFront(element) {
    const boxes = document.querySelectorAll('.box');
    boxes.forEach(box => {
        box.style.zIndex = 1;
    });
    element.style.zIndex = 10;
}

function adjustBoxes(imageElement, index) {
    const currentWidth = imageElement.width();
    const currentHeight = imageElement.height();

    const boxes = $('.processed-image-wrapper').eq(index).find('.box');
    boxes.each(function (boxIndex) {
        const left = originalBoxes[index][boxIndex].x;
        const top = originalBoxes[index][boxIndex].y;
        const newLeft = (left / originalWidth) * currentWidth;
        const newTop = (top / originalHeight) * currentHeight;
        $(this).css({ left: newLeft + 'px', top: newTop + 'px' });
    });
}

function logDivsByRow() {
    const boxes = Array.from(document.querySelectorAll('.box'));

    boxes.sort((a, b) => a.offsetTop - b.offsetTop);

    const rowThreshold = 20;  

    const rows = [];
    let currentRow = [boxes[0]];  

    for (let i = 1; i < boxes.length; i++) {
        const currentBox = boxes[i];
        const previousBox = boxes[i - 1];

        if (Math.abs(currentBox.offsetTop - previousBox.offsetTop) <= rowThreshold) {
            currentRow.push(currentBox);
        } else {
            rows.push(currentRow);
            currentRow = [currentBox];
        }
    }

    rows.push(currentRow);

    let output = '';
    rows.forEach(row => {
        const rowText = row.map(box => box.textContent.trim()).join(' ');
        output += rowText + '\n';
    });

    console.log(output);
}

function handleFileUpload() {
    const input = document.getElementById('imageInput');
    const files = input.files;
    const previewContainer = document.getElementById('previewContainer');
    const maxFiles = 5;
    const allowedFileTypes = ['image/jpeg', 'image/png'];

    previewContainer.innerHTML = '';
    
    const selectedFiles = Array.from(files).slice(0, maxFiles);

    selectedFiles.forEach(file => {
        if (allowedFileTypes.includes(file.type)) {
            const reader = new FileReader();
            reader.onload = function (e) {
                const imgElement = document.createElement('img');
                imgElement.src = e.target.result;
                previewContainer.appendChild(imgElement);
            };
            reader.readAsDataURL(file);
        } else {
            alert('Only JPG, JPEG, and PNG files are allowed.');
        }
    });

    if (selectedFiles.length > maxFiles) {
        alert(`Only the first ${maxFiles} files will be processed.`);
    }
}

function updateTextareaForImage(imageIndex) {
    const textarea = $('textarea').eq(imageIndex);
    const boxTexts = [];
    const boxes = $('.processed-image-wrapper').eq(imageIndex).find('.box');
    let previousText = '';

    boxes.each(function () {
        let currentText = $(this).text();

        if (currentText === '@' || currentText === '.' || currentText === ':') {
            if (boxTexts.length > 0 && boxTexts[boxTexts.length - 1] === ' ') {
                boxTexts.pop();
            }
            boxTexts.push(currentText);
        } else {
            if (previousText !== '@' && previousText !== '.' && previousText !== ':' && previousText !== '') {
                boxTexts.push(' ');
            }
            boxTexts.push(currentText);
        }

        previousText = currentText;
    });

    textarea.val(boxTexts.join('').trim());
}

