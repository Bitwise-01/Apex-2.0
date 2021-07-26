"use strict";

const fadingAlert = (msg, severity = 2) => {
	const level =
		severity === 0
			? "alert-success"
			: severity === 1
			? "alert-warning"
			: "alert-danger";

	const alertMessage = $("#alert-message");
	const alertDisplayTime = 2500;

	alertMessage.addClass(level);
	alertMessage.text(msg);
	alertMessage.fadeIn();
	setTimeout(() => alertMessage.fadeOut("slow"), alertDisplayTime);
};
