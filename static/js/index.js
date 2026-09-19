(() => {
  "use strict";

  menuBar();

  bgImg();

  //venoBox();

  //testimonialSlider();

  //accordionPClass();

  //clindLogoSlider();

  //workProsessSlider();

  //collaborationSlider();

  animeCounterUp();

  htmlFatchFrom();

  //wow();

  bottomToTop();

  // preloderOption();

  /*====== Active Plugins ======

        1 Menu Bar

        2 BG Img

        3 VenoBox

        4 Testimonial Slider

        5 Accordion P Class

        6 Clind Logo Slider

        7 WorkProsess Slider

        8 Collaboration Slider

        9 Anime Counter Up

        10 HTML Fatch From

        11 WOW

        12 Back To Top

        13 Preloder Option

    =============================*/

  /*=====================
      1 Menu Bar
  =======================*/
  function menuBar() {
    let copyMenuList = $(".menu-bar .main-menu ul").html();
    $(".menu-bar .menu-bar-content").append(`<div class="mobile-menu-overlay">`);
    $("h2").append(`<div class="swiper-pagination-bullet-active">`);

    $(".menu-bar .mobile-menu-btn").on("click", function () {
      $(this).addClass("active");
      $(this).parents(".menu-bar-content").find(".mobile-menu-bar").addClass("active");
      $(this).parents(".menu-bar-content").find(".mobile-menu-overlay").addClass("active");
    });

    $(".menu-bar .close-mobile-btn, .menu-bar .mobile-menu-overlay").on("click", function () {
      $(this).parents(".menu-bar-content").find(".mobile-menu-bar, .mobile-menu-btn, .mobile-menu-overlay").removeClass("active");
      }
    );

    $(".menu-bar .mobile-menu-bar .mobile-menu-header").after(`
      <nav class="mobile-main-manu">
        <ul>${copyMenuList}</ul>
      </nav>
    `);

    $(".menu-bar .mobile-main-manu li:has(ul) > a").on("click", function (e) {
      e.preventDefault();
      const $parent = $(this).parent("li");
      const $siblings = $parent.siblings("li");
      const isActive = $parent.hasClass("active");
      if (isActive) {
        $parent.removeClass("active");
        $parent.find("ul").slideUp();
      } else {
        $parent.addClass("active");
        $siblings.removeClass("active");
        $siblings.children("ul:visible").slideUp();
        $parent.children("ul").slideDown();
      }
    });

    $(".menu-bar .mobile-main-manu .has-dropdown").find(".active").parent().slideDown();
    
    $(window).scroll(() => {
      let menuBar = $(".menu-bar");

      if (menuBar.hasClass("v1")){
        if ($(window).scrollTop() > 0) {
          menuBar.addClass("sticky-header");
        } else {
          menuBar.removeClass("sticky-header");
        }
      } 
      else if (menuBar.hasClass("v2") || menuBar.hasClass("v3")){
        let scrollTop = $(window).scrollTop();
        let shouldAddSticky = (screen.width >= 576 && scrollTop > 20) || (screen.width <= 576 && scrollTop > 0);

        if (shouldAddSticky) {
          menuBar.addClass("sticky-header");
        } else {
          menuBar.removeClass("sticky-header");
        }
      }

    });
  }

  /*=====================
      2 BG Img
  =======================*/
  function bgImg() {
    document.querySelectorAll("[data-background]").forEach((element) => {
      element.style.backgroundImage = `url(${element.getAttribute(
        "data-background"
      )})`;
    });
  }

  /*========================
      3 VenoBox
  =======================*/
  function venoBox() {
    new VenoBox();
  }

  /*===========================
      4 Testimonial Slider
  =============================*/
  /*function testimonialSlider(){
    let testimonialSlider1 = new Swiper(".testimonial.v1 .slider", {
      slidesPerView: 1,
      spaceBetween: 30,
      loop: true,
      speed: 1000,
      autoplay: {
        delay: 3000,
        disableOnInteraction: false,
        pauseOnMouseEnter: true,
      },
      navigation: {
        nextEl: ".next-btn",
        prevEl: ".prev-btn",
      },
      pagination: {
        el: ".testimonial.v2 .testimonial-pagination",
        clickable: true,
      },
      breakpoints: {
        300: {
          slidesPerView: 1,
        },
        992: {
          slidesPerView: 2,
        },
      },
    });
    let testimonialSlider2 = new Swiper(".testimonial.v2 .slider", {
      slidesPerView: 1,
      spaceBetween: 30,
      loop: true,
      speed: 1000,
      autoplay: {
        delay: 3000,
        disableOnInteraction: false,
        pauseOnMouseEnter: true,
      },
      navigation: {
        nextEl: ".next-btn",
        prevEl: ".prev-btn",
      },
      pagination: {
        el: ".testimonial.v2 .testimonial-pagination",
        clickable: true,
      },
      breakpoints: {
        300: {
          slidesPerView: 1,
        },
        992: {
          slidesPerView: 2,
        },
      },
    });

    let testimonialSlider3 = new Swiper(".testimonial.v3 .slider", {
      slidesPerView: 1,
      spaceBetween: 30,
      loop: true,
      speed: 1000,
      autoplay: {
        delay: 3000,
        disableOnInteraction: false,
        pauseOnMouseEnter: true,
      },
    });
  }
*/
  /*===========================
      5 Accordion P Class
  ==========================*/
  function accordionPClass() {
    $(".accordion-btn").on("click", function () {
      $("li").removeClass("active");
      $(this).parents("li").toggleClass("active");
    });
  }

  /*========================
      6 Clind Logo Slider
  =======================*/
  /*function clindLogoSlider() {
    let clindLogoSlider = new Swiper(".clind-logo .slider", {
      spaceBetween: 30,
      loop: true,
      speed: 900,
      autoplay: {
        delay: 500,
        disableOnInteraction: false,
        pauseOnMouseEnter: true,
      },
      breakpoints: {
        300: {
          slidesPerView: 2,
        },
        575: {
          slidesPerView: 3,
        },
        767: {
          slidesPerView: 4,
        },
        992: {
          slidesPerView: 4,
        },
        1200: {
          spaceBetween: "11%",
          slidesPerView: 5,
        },
        1400: {
          spaceBetween: "13%",
          slidesPerView: 5,
        },
      },
    });
  } */


  /*===========================
      7 WorkProsess Slider
  =============================
  function workProsessSlider(){
    let workProsessSlider1 = new Swiper(".work-process.v2 .slider", {
      slidesPerView: 1,
      spaceBetween: 30,
      loop: true,
      speed: 1000,
      autoplay: {
        delay: 3000,
        disableOnInteraction: false,
        pauseOnMouseEnter: true,
      },
      navigation: {
        nextEl: ".work-process.v2 .next-btn",
        prevEl: ".work-process.v2 .prev-btn",
      },
    });
  } */

  /*=======================================
      8 Collaboration Slider
  =========================================
  function collaborationSlider(){
    let collaborationSlider1 = new Swiper(".collaboration.v2 .slider", {
      slidesPerView: 1,
      spaceBetween: 30,
      loop: true,
      speed: 1000,
      autoplay: {
        delay: 3000,
        disableOnInteraction: false,
        pauseOnMouseEnter: true,
      },
      navigation: {
        nextEl: ".collaboration.v2 .next-btn",
        prevEl: ".collaboration.v2 .prev-btn",
      },
      pagination: {
        el: ".collaboration.v2 .collaboration-pagination",
        clickable: true,
      },
      breakpoints: {
        300: {
          slidesPerView: 1,
        },
        768: {
          slidesPerView: 2,
        },
        1200: {
          slidesPerView: 3,
        },
      },
    });
  }
  */
  /*========================
      9 Anime Counter Up
  =======================*/
  function animeCounterUp() {
    const $counterElements = $(".counter");

    function animateElement(element) {
      if (!element.dataset.animated) {
        const originalText = element.textContent; // Capture the original text before animation
        anime({
          targets: element,
          innerHTML: [
            parseInt(element.dataset.countMin) || 0,
            parseInt(element.dataset.countMax),
          ],
          round: 1,
          easing: "linear",
          duration: parseInt(element.dataset.countDuration) || 1000,
          delay: parseInt(element.dataset.countDelay) || 500,
          complete: function (anim) {
            // Animation is complete, restore the original text
            element.textContent = originalText;
          },
        });

        element.dataset.animated = true; // Set the animated flag to prevent re-animating
      }
    }

    const isElementInViewport = (el) => {
      const rect = el.getBoundingClientRect();
      return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <=
          (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <=
          (window.innerWidth || document.documentElement.clientWidth)
      );
    };

    const handleScroll = () => {
      $counterElements.each(function () {
        if (isElementInViewport(this)) {
          animateElement(this); // Animate the current counter element if not already animated
        }
      });
    };

    $counterElements.each(function () {
      if (isElementInViewport(this)) {
        animateElement(this); // Animate initially visible counter elements
      }
    });

    $(window).on("scroll", handleScroll);
  }

  /*=====================
      10 HTML Fatch From 
  =======================*/
  function htmlFatchFrom() {
    if ($("form").hasClass("message-form")) {
      // Get the form.
      const form = document.querySelector(".message-form");

      // Get the messages div.
      const formMessages = $(".response");

      // Set up an event listener for the contact form.
      form.addEventListener("submit", (event) => {
        // Stop the browser from submitting the form.
        event.preventDefault();

        // Serialize the form data.
        const formData = new FormData(form);

        // Perform form field validation here.
        if (!validateFormFields(formData, formMessages)) {
          return;
        }

        // Submit the form using Fetch.
        fetch(form.action, {
          method: "POST",
          body: formData,
        })
          .then((response) => response.text())
          .then((responseText) => {
            // Make sure that the formMessages div has the 'success' class.
            formMessages.removeClass("error");
            formMessages.addClass("success");

            // Set the message text.
            formMessages.text(responseText);
            form.reset();

            // Use Anime.js for animations.
            animateFormMessages(formMessages);
          })
          .catch((error) => {
            // Use Anime.js for error animations.
            animateFormMessages(formMessages, error);

            // Make sure that the formMessages div has the 'error' class.
            formMessages.removeClass("success");
            formMessages.addClass("error");

            formMessages.text(
              `${
                error
                  ? error
                  : "Oops! An error occurred and your message could not be sent."
              }`
            );
          });
      });
    }

    function validateFormFields(formData, formMessages) {
      // You can add your custom form field validation logic here.
      // Check the formData object for the values of the form fields and update the formMessages element with error messages.

      const firstname = formData.get("firstname");
      const lastname = formData.get("lastname");
      const username = formData.get("username");
      const number = formData.get("number"); // Assuming the input field for number is named "number."
      const message = formData.get("message"); // Assuming the input field for the message is named "message."

      if (!firstname || firstname.trim() === "") {
        animateFormMessages(formMessages, "Please enter your first name.", "error");
        return false;
      }

      if (!lastname || lastname.trim() === "") {
        animateFormMessages(formMessages, "Please enter your last name.", "error");
        return false;
      }

      if (!username || username.trim() === "") {
        animateFormMessages(formMessages, "Please enter your user name.", "error");
        return false;
      }

      // number number validation using a regular expression (10 digits, optional dashes or spaces).
      const numberRegex = /^(\d{10}|\d{3}[-\s]\d{3}[-\s]\d{4})$/;
      if (!numberRegex.test(number)) {
        animateFormMessages(
          formMessages,
          "Please enter a valid number number (e.g., 123-456-7890 or 1234567890).",
          "error"
        );
        return false;
      }

      if (!message || message.trim() === "") {
        animateFormMessages(formMessages, "Please enter a message.", "error");
        return false;
      }

      // Clear any previous error messages.
      formMessages.empty();
      return true;
    }

    function animateFormMessages(
      formMessages,
      message,
      messageType = "success"
    ) {
      // Use Anime.js for animations.
      const timeline = anime.timeline();
      timeline
        .add({
          targets: formMessages[0],
          opacity: [0, 1],
          translateY: [50, 0],
          easing: "easeInOutQuad",
          duration: 400,
        })
        .add({
          targets: formMessages[0],
          opacity: [1, 0],
          translateY: [0, -50],
          easing: "easeInOutQuad",
          duration: 400,
          delay: messageType === "error" ? 2000 : 6000, // Adjust delay as needed.
          complete: () => {
            formMessages.empty();
            formMessages.removeClass(messageType);
          },
        });

      formMessages.removeClass(messageType === "error" ? "success" : "error");
      formMessages.addClass(messageType);
      formMessages.text(message);
    }
  }

  /*============================
      11 WOW
  ===========================
  function wow() {
    let wow = new WOW({
      animateClass: "animate__animated",
      offset: 0,
    });
    wow.init();
  }
  */
  /*============================
      12 Back To Top
  =============================*/
  function bottomToTop() {
    let scrollTop = $(".scroll-bottom-top");

    let sectionScrollHight = $("main")
      .find(".banner,.breadcum")
      .first()
      .outerHeight();

    $(window).scroll(function () {
      if ($(window).scrollTop() > sectionScrollHight / 2) {
        scrollTop.addClass("show");
      } else {
        scrollTop.removeClass("show");
      }
    });

    scrollTop.on("click", function (e) {
      e.preventDefault();
      $("html, body").animate({ scrollTop: 0 }, "300");
    });
  }

  /*============================
      13 Preloder Option
  =============================*/
  /*
  function preloderOption() {
    window.addEventListener("load", () => {
      const preloader = document.querySelector(".preloder");
      document.querySelector('body .preloder').insertAdjacentHTML('afterbegin', '<div class="loader"></div>');

      anime({
        targets: preloader,
        opacity: 0,
        delay: 500, // Delay in milliseconds
        duration: 400, // Duration in milliseconds
        easing: 'linear', // Easing function for the animation
        complete: function() {
          preloader.remove();
        }
      });
    });
  }
    */
  
})();