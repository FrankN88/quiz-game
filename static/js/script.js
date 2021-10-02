/*
	HOME PAGE ANIMATIONS
*/
if($(".page_home").length){

	// Hide footer to show it later
	$("footer").hide();
	
	// Move the logo and show it
	$(".logo-home").css({
		marginTop: "-200px",
		opacity: 0,
	}).animate({
		marginTop: "0px",
		opacity: 1,
	},750);

	// Move the quiz link and show it
	$(".link-quiz").css({
		left: "-300px",
		opacity: 0
	}).animate({
		left: "0px",
		opacity: 1
	},750);

	// Move the login link and show it
	$(".link-login").css({
		right: "-300px",
		opacity: 0
	}).animate({
		right: "0px",
		opacity: 1
	},750,function(){

		// Show the footer only after the other elements have appeared
		$("footer").fadeIn();
	});

}


/*
	LOGIN AND REGISTRATION PAGES ANIMATION
*/
if($(".page_login, .page_registration").length){

	// Hide footer to show it later
	$("footer").hide();
	
	// Prepare the form for the animations
	$("form").css({
		marginTop: "-100px",
		opacity: 0,
	}).animate({
		marginTop: "30px",
		opacity: 1,
	},750,function(){

		// Show the footer only after the other elements have appeared
		$("footer").fadeIn();
		$("[name='username']").focus();
	});

}

/*
	QUIZ PAGE ANIMATION
*/
if($(".page_quiz").length){

	if(
		!$(".answers").hasClass("correct") &&		
		!$(".answers").hasClass("wrong")
	){

		// Show animation only if there is no answer
		$(".answer").css({
			opacity: 0,
			left: "-50px"
		});

		// Show the buttons one after the other
		// Set delay to zero (for the first button)
		var delay = 0;
		$(".answer").each(function(index,el){
			
			// Do animation after delay
			$(el).delay(delay).animate({
				opacity:1,
				left: 0
			},750);

			//Increment delay
			delay += 200;
		});

	}

}

/*
	SCROLL TO TOP - ANIMATION + SCROLL
*/
$(window).scroll(function(){
	var pos = window.scrollY;
	if(pos > 50){
		$(".scroll_to_top").show();
	}else{
		$(".scroll_to_top").hide();		
	}
});
$(".scroll_to_top").click(function(){
	$("html, body").animate({scrollTop:0}, 500);
});