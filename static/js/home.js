{# 
function redirectToPage() {
    window.location.href = "/sign.up";
}

let textPosition = 0;
let speed = 15;

const res = "{{random_suggestion}}".replace(/&#39;/g, "'");

const typeWriter = () => {
const txtHolder = document.getElementById("bemeneti_szoveg");
txtHolder.value = res.substring(0, textPosition) + "\u25ae";
if (textPosition++ < res.length) {
setTimeout(typeWriter, speed);
} else {
const imageHolder = document.getElementById('generated-image-homepage');
if (imageHolder) {
    imageHolder.innerHTML = `<div class="dot-windmill-container">
<div class="snippet" data-title="dot-windmill">
  <div class="stage">
    <div class="dot-windmill"></div>
  </div>
</div>
</div>`
}
setTimeout(() => {
            // Change to an img div element
            imageHolder.innerHTML = `
            <img src="./static/bemutato-kepek-static/kep/{{random_image}}" alt="Random Image">`;

            // Enable the button
            const button = document.getElementById('letrehozas'); // Replace with your actual button ID
            if (button) {
                button.disabled = false; // Enable the button
            }
        }, 2000);
setTimeout(() => {
    txtHolder.value = res;
}, 0);
}
};

window.onload = typeWriter;

$('#letrehozas').click(function() {
    var inputValue = $('#bemeneti_szoveg').val();
    $("#letrehozas").attr('disabled', true);

    const imageHolder = document.getElementById('generated-image-homepage');
if (imageHolder) {
    imageHolder.innerHTML = `<div class="dot-windmill-container">
<div class="snippet" data-title="dot-windmill">
  <div class="stage">
    <div class="dot-windmill"></div>
  </div>
</div>
</div>`
}

    $.ajax({
    type: 'POST',
    url: '/index_generate_images',
    contentType: 'application/json',
    data: JSON.stringify({inputValue: inputValue}),
    success: function(response) {
        clearTimeout(timeout);
        if (response.hasOwnProperty('success')) {
    imageHolder.innerHTML = '<img src="' + response.success + '" alt="Your generated image"">';           
        }
        else {
            alert(response.message)
        }
    }})}
    )

#}