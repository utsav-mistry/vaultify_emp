// Menu toggle
var toggle = document.querySelector('.toggle-custom');
var navigation = document.querySelector('.navigation-custom');
var main = document.querySelector('.main-custom');
toggle.addEventListener('click', function () {
    navigation.classList.toggle('active');
    main.classList.toggle('active');
});

// Navigation functionality
var navLinks = document.querySelectorAll('.navigation-custom ul li a');
var sections = document.querySelectorAll('.section');

function openSection(link) {
    var sectionId = link.getAttribute('data-section');
    for (var i = 0; i < sections.length; i++) {
        sections[i].style.display = 'none';
    }
    var activeSection = document.getElementById(sectionId);
    if (activeSection) {
        activeSection.style.display = 'block';
    }
}

for (var i = 0; i < navLinks.length; i++) {
    navLinks[i].addEventListener('click', function (e) {
        e.preventDefault();
        for (var j = 0; j < navLinks.length; j++) {
            navLinks[j].parentElement.classList.remove('active');
        }
        this.parentElement.classList.add('active');
        openSection(this);
    });
}
