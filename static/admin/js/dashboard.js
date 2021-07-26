(() => {
	"use strict";

	// ----------------------- Start EventSources ----------------------- //

	const accesspointScanOutputURL = "/accesspoints/scan-output";
	let accesspointScanOutput = null;

	const handshakeOutputURL = "/handshake/output-process";
	let handshakeOutput = null;

	const eviltwinOutputURL = "/eviltwin/output-eviltwin";
	let eviltwinOutput = null;

	// ----------------------- Ends EventSources ----------------------- //

	const scanSection = $("#details");
	const scanTab = $('.nav-link[data-target="#details"]');
	const startScanBtn = $("#start-scan");
	const startScanLoader = $("#start-scan-loader");

	const stopScanBtn = $("#stop-scan");
	const stopScanLoader = $("#stop-scan-loader");

	const enableMonModeBtn = $("#enable-mon-mode");
	const enableMonModeLoader = $("#enable-mod-mode-loader");

	const disableMonModeBtn = $("#disable-mon-mode");
	const disableMonModeLoader = $("#disable-mod-mode-loader");

	const handshakeSection = $("#handshake");
	const handshakeTab = $('.nav-link[data-target="#handshake"]');

	const startHandshakeBtn = $("#start-handshake");
	const startHandshakeLoader = $("#start-handshake-loader");

	const stopHandshakeBtn = $("#stop-handshake");
	const stopHandshakeLoader = $("#stop-handshake-loader");

	const eviltwinSection = $("#evil-twin");
	const eviltwinTab = $('.nav-link[data-target="#evil-twin"]');

	const startEviltwinBtn = $("#start-eviltwin");
	const startEviltwinLoader = $("#start-eviltwin-loader");

	const stopEviltwinBtn = $("#stop-eviltwin");
	const stopEviltwinLoader = $("#stop-eviltwin-loader");

	const _interface = $("#interface");

	const refreshOutput = $("#refresh-output");

	const minIdealPower = -74;
	const minIdealClients = 2;

	const privacyCode = {
		OPN: "text-success",
		WEP: "text-warning",
		WPA: "text-warning",
		WPA2: "text-danger",
	};

	let isMonitorMode = undefined;

	let isScanning = false;
	let accesspoints = undefined;
	let refreshingOutput = false;
	let currentAccesspointBssid = null;

	let handshakeTarget = null;
	let isListeningForHandshake = false;

	let clients = undefined;
	let eviltwinTarget = null;
	let currentClientMac = null;
	let isListeningForPassphrase = false;

	let capturedAccesspoints = null;
	let SelectedCapturedAccesspointBssid = null;

	$(document).ready(() => {
		syncWithServer();
	});

	// ----------------------- Start Sync ----------------------- //

	const syncWithServer = () => {
		// Interface info
		$.ajax({
			type: "GET",
			url: "/interface/status",
		}).done((resp) => {
			if (resp.status !== 1) {
				location.reload();
				return;
			}

			const status = resp.value;

			isMonitorMode = status["monitor-mode"];

			if (!isMonitorMode) {
				enableMonModeBtn.show();
				disableMonModeBtn.hide();
				return;
			}

			const intf = status["interface"];

			if (intf === undefined) {
				enableMonModeBtn.hide();
				disableMonModeBtn.hide();
				return;
			}

			enableMonModeBtn.hide();
			disableMonModeBtn.show();

			_interface.val(intf);
			_interface.prop("disabled", true);
			startScanBtn.prop("disabled", false);

			if (
				(handshakeTarget && handshakeTarget.isActive) ||
				(eviltwinTarget && eviltwinTarget.isActive)
			) {
				disableMonModeBtn.prop("disabled", true);
				toggleTabs(false);
			}
		});

		// Scanning info
		$.ajax({
			type: "GET",
			url: "/accesspoints/status",
		}).done((resp) => {
			if (resp.status !== 1) {
				location.reload();
				return;
			}

			const status = resp.value;

			if (!status["scanning"]) {
				startScanBtn.show();
				stopScanBtn.hide();
				return;
			}

			isScanning = true;
			startScanning();
			startScanBtn.hide();
			stopScanBtn.show();
			disableMonModeBtn.prop("disabled", true);
			refreshOutput.prop("disabled", false);
			startAccesspointScanOutput();
		});

		// Accesspoints
		$.ajax({
			type: "GET",
			url: "/accesspoints/get-aps",
		}).done((resp) => {
			if (resp.status === 1) {
				processAccesspoints(resp.value);
				resumeEviltwinState();
			}
		});

		// Captured accesspoints
		getCapturedAps();
	};

	const resumeHandshakeState = () => {
		$.ajax({
			type: "GET",
			url: "/handshake/status",
		}).done((resp) => {
			if (resp.status === 1) {
				handshakeTarget = resp.value.target;

				if (handshakeTarget === null) {
					return;
				} else {
					// rerender accesspoints

					$.ajax({
						type: "GET",
						url: "/accesspoints/get-aps",
					}).done((resp) => {
						if (resp.status === 1) {
							processAccesspoints(resp.value);
						}
					});
				}

				if (!handshakeTarget.isActive) {
					return;
				}

				if (!handshakeTarget.bssid in accesspoints) {
					stopHandshake(false);
					return;
				}

				isListeningForHandshake = true;
				selectAccesspoint(handshakeTarget.bssid, false);
				scrollToSelectedAccesspoint();

				startHandshakeBtn.hide();
				stopHandshakeBtn.show();
				startHandshakeOutput();
			}
		});
	};

	const resumeEviltwinState = (refreshAps = true) => {
		$.ajax({
			type: "GET",
			url: "/eviltwin/status",
		}).done((resp) => {
			eviltwinTarget = resp.value.eviltwin || null;

			if (
				resp.status === 1 &&
				resp.value &&
				Object.keys(resp.value).length &&
				eviltwinTarget &&
				!eviltwinTarget.isFound
			) {
				isListeningForPassphrase = true;
				startEviltwinBtn.hide();
				stopEviltwinBtn.show();

				isListeningForPassphrase = true;
				startEviltwinOutput();
			} else {
				startEviltwinBtn.show();
				stopEviltwinBtn.hide();
			}

			resumeHandshakeState();
		});
	};

	// ----------------------- End Sync ----------------------- //

	// ----------------------- Start Interface ----------------------- //

	const enableMonModeDisableBtn = () => {
		if (!isScanning && !isListeningForHandshake && !isListeningForPassphrase) {
			disableMonModeBtn.prop("disabled", false);
		}
	};

	enableMonModeBtn.on("click", () => {
		if (_interface.val().trim().length === 0) {
			return;
		}

		// Enabling monitor mode...
		enableMonModeBtn.hide();
		enableMonModeLoader.show();
		_interface.prop("disabled", true);

		$.ajax({
			type: "POST",
			url: "/interface/enable-mon-mode",
			data: { interface: _interface.val() },
		}).done((resp) => {
			enableMonModeLoader.hide();

			if (resp.status !== 1) {
				enableMonModeBtn.show();
				_interface.prop("disabled", false);

				if (resp.msg.length) {
					fadingAlert(resp.msg, 3);
				} else {
					fadingAlert(`Error: Unknown`, 3);
				}

				return;
			}

			isMonitorMode = true;
			disableMonModeBtn.show();
			startScanBtn.prop("disabled", false);

			if (currentAccesspointBssid !== null) {
				toggleTabs();
			}
		});
	});

	disableMonModeBtn.on("click", () => {
		// Disabling monitor mode...
		disableMonModeBtn.hide();
		disableMonModeLoader.show();

		$.ajax({
			type: "POST",
			url: "/interface/disable-mon-mode",
		}).done((resp) => {
			disableMonModeLoader.hide();

			if (resp.status !== 1) {
				disableMonModeBtn.show();
				if (resp.msg.length) {
					fadingAlert(`Error: ${resp.msg}`, 3);
				} else {
					fadingAlert("Error: Unkown", 3);
				}
				return;
			}

			isMonitorMode = false;
			enableMonModeBtn.show();
			_interface.prop("disabled", false);
			startScanBtn.prop("disabled", true);

			toggleTabs();
		});
	});

	// ----------------------- End Interface ----------------------- //

	// ----------------------- Start Accesspoint ----------------------- //

	const processAccesspoints = (aps) => {
		accesspoints = aps;
		let tableRow;

		if (aps === undefined || aps === null) {
			location.reload();
			return;
		}

		$("#networks-display").text("");
		$("#total-networks").text(Object.keys(aps).length);

		$.each(aps, (_, ap) => {
			tableRow = $("<tr>");

			if (handshakeTarget && handshakeTarget.bssid === ap["bssid"]) {
				if (handshakeTarget.isCaptured) {
					if (eviltwinTarget === null) {
						tableRow.append(
							$("<td>", {
								"data-bssid": ap["bssid"],
								class: "bssid clickable text-success",
								title: "Handshake captured",
							}).text(ap["bssid"])
						);
					} else {
						if (!eviltwinTarget.isFound && eviltwinTarget.isActive) {
							tableRow.append(
								$("<td>", {
									"data-bssid": ap["bssid"],
									class: "bssid clickable text-info",
									title: "Eviltwin active",
								}).text(ap["bssid"])
							);
						} else if (!eviltwinTarget.isFound && !eviltwinTarget.isActive) {
							tableRow.append(
								$("<td>", {
									"data-bssid": ap["bssid"],
									class: "bssid clickable",
									style: "color: var(--orange)",
									title: "Eviltwin inactive",
								}).text(ap["bssid"])
							);
						} else if (eviltwinTarget.isFound) {
							tableRow.append(
								$("<td>", {
									"data-bssid": ap["bssid"],
									class: "bssid clickable text-primary",
									title: "Password found",
								}).text(ap["bssid"])
							);
						}
					}
				} else if (handshakeTarget.isActive) {
					tableRow.append(
						$("<td>", {
							"data-bssid": ap["bssid"],
							class:
								"bssid clickable " +
								(+ap["power"] !== 0 ? "text-warning" : "text-danger"),
							title: "Capturing handshake",
						}).text(ap["bssid"])
					);
				} else {
					tableRow.append(
						$("<td>", {
							"data-bssid": ap["bssid"],
							class: "bssid clickable",
							title: "Handshake Captured",
						}).text(ap["bssid"])
					);
				}
			} else {
				tableRow.append(
					$("<td>", {
						"data-bssid": ap["bssid"],
						class: "bssid clickable",
					}).text(ap["bssid"])
				);
			}

			tableRow.append(
				$("<td>", { class: "essid", title: ap["essid"] }).text(
					ap["essid"].length >= 32
						? ap["essid"].slice(0, 14) + "..."
						: ap["essid"]
				)
			);

			const power = parseInt(ap["power"]);
			const clients = ap["clients"];
			const privacy = ap["privacy"].split(" ")[0].toUpperCase();

			let powerColorCode = undefined;
			let clientColorCode = undefined;
			let privacyColorCode = privacy in privacyCode ? privacyCode[privacy] : "";

			if (power >= minIdealPower) {
				powerColorCode =
					clients.length >= minIdealClients ? "text-success" : "text-warning";
			} else {
				powerColorCode =
					clients.length >= minIdealClients ? "text-warning" : "text-danger";
			}

			if (power >= minIdealPower) {
				clientColorCode =
					clients.length >= minIdealClients ? "text-success" : "text-warning";
			} else {
				clientColorCode =
					clients.length >= minIdealClients ? "text-success" : "text-danger";
			}

			tableRow.append($("<td>", { class: "chann" }).text(ap["chann"]));
			tableRow.append($("<td>", { class: privacyColorCode }).text(privacy));
			tableRow.append(
				$("<td>", { class: powerColorCode, title: ap["ap_score"] }).text(
					ap["power"]
				)
			);
			tableRow.append(
				$("<td>", { class: clientColorCode }).text(clients.length)
			);

			if (
				handshakeTarget &&
				handshakeTarget.isCaptured &&
				handshakeTarget.bssid === ap["bssid"]
			) {
				$("#networks-display").prepend(tableRow);
			} else {
				$("#networks-display").append(tableRow);
			}
		});

		setSelectedAccesspoint();
		if ($("#follow-ap").is(":checked")) {
			scrollToSelectedAccesspoint();
		}
	};

	const updateSelectedAccesspointDetails = () => {
		if (currentAccesspointBssid === null) {
			return;
		}

		const accesspoint = accesspoints[currentAccesspointBssid];

		if (accesspoint === null || accesspoint === undefined) {
			currentAccesspointBssid = null;
			return;
		}

		const apDetails = $("#ap-detail-output");
		const section1 = $("<li>");
		const section2 = $("<li>");
		const section3 = $("<li>");
		const section4 = $("<li>");
		const section5 = $("<li>");

		["bssid", "essid"].forEach((e) => {
			const p = $("<p>", { class: "ap-detail-cont" });

			p.append($("<span>", { class: "ap-detail-tag" }).append(e)).append(
				$("<span>", { class: "ap-detail-value" }).append(accesspoint[e])
			);

			section1.append(p);
		});

		section2
			.append(
				$("<p>", { class: "ap-detail-cont" })
					.append($("<span>", { class: "ap-detail-tag" }).append("Channel"))
					.append(
						$("<span>", { class: "ap-detail-value" }).append(
							accesspoint["chann"]
						)
					)
			)
			.append(
				$("<p>", { class: "ap-detail-cont" })
					.append($("<span>", { class: "ap-detail-tag" }).append("Power"))
					.append(
						$("<span>", { class: "ap-detail-value" }).append(
							accesspoint["power"]
						)
					)
			)
			.append(
				$("<p>", { class: "ap-detail-cont" })
					.append($("<span>", { class: "ap-detail-tag" }).append("Clients"))
					.append(
						$("<span>", { class: "ap-detail-value" }).append(
							Object.keys(accesspoint["clients"]).length
						)
					)
			);

		section3
			.append(
				$("<p>", { class: "ap-detail-cont" })
					.append($("<span>", { class: "ap-detail-tag" }).append("First Seen"))
					.append(
						$("<span>", { class: "ap-detail-value" }).append(
							accesspoint["first_seen"]
						)
					)
			)
			.append(
				$("<p>", { class: "ap-detail-cont" })
					.append($("<span>", { class: "ap-detail-tag" }).append("Last Seen"))
					.append(
						$("<span>", { class: "ap-detail-value" }).append(
							accesspoint["last_seen"]
						)
					)
			);

		section4
			.append(
				$("<p>", { class: "ap-detail-cont" })
					.append(
						$("<span>", { class: "ap-detail-tag" }).append("Authentication")
					)
					.append(
						$("<span>", { class: "ap-detail-value" }).append(
							accesspoint["authen"]
						)
					)
			)
			.append(
				$("<p>", { class: "ap-detail-cont" })
					.append($("<span>", { class: "ap-detail-tag" }).append("Privacy"))
					.append(
						$("<span>", { class: "ap-detail-value" }).append(
							accesspoint["privacy"]
						)
					)
			)
			.append(
				$("<p>", { class: "ap-detail-cont" })
					.append($("<span>", { class: "ap-detail-tag" }).append("Cipher"))
					.append(
						$("<span>", { class: "ap-detail-value" }).append(
							accesspoint["cipher"]
						)
					)
			);

		section5
			.append(
				$("<p>", { class: "ap-detail-cont" })
					.append($("<span>", { class: "ap-detail-tag" }).append("Beacons"))
					.append(
						$("<span>", { class: "ap-detail-value" }).append(
							accesspoint["beacons"]
						)
					)
			)
			.append(
				$("<p>", { class: "ap-detail-cont" })
					.append($("<span>", { class: "ap-detail-tag" }).append("Speed"))
					.append(
						$("<span>", { class: "ap-detail-value" }).append(
							accesspoint["speed"]
						)
					)
			)
			.append(
				$("<p>", { class: "ap-detail-cont" })
					.append($("<span>", { class: "ap-detail-tag" }).append("IVs"))
					.append(
						$("<span>", { class: "ap-detail-value" }).append(accesspoint["iv"])
					)
			);

		apDetails.text("");
		apDetails.append(section1);
		apDetails.append(section2);
		apDetails.append(section3);
		apDetails.append(section4);
		apDetails.append(section5);
	};

	const updateSelectedAccesspointClients = () => {
		if (currentAccesspointBssid === null) {
			return;
		}

		const accesspoint = accesspoints[currentAccesspointBssid];

		if (accesspoint === null) {
			currentAccesspointBssid = null;
			return;
		}

		let tableRow = undefined;
		const clientsTable = $("#client-display");

		clientsTable.text("");

		accesspoint["clients"].forEach((client) => {
			tableRow = $("<tr>");

			if (parseInt(client["power"]) === -1) {
				tableRow.addClass("bg-danger");
			}

			tableRow.append($("<td>", { class: "bssid" }).text(client["mac"]));
			tableRow.append($("<td>").text(client["power"]));
			tableRow.append($("<td>").text(client["packets"]));
			tableRow.append($("<td>").text(client["first_seen"]));
			tableRow.append($("<td>").text(client["last_seen"]));

			clientsTable.append(tableRow);
		});
	};

	const setSelectedAccesspoint = () => {
		$(".bssid.clickable").each((_, td) => {
			const $tr = $(td.parentElement);
			if (td.dataset.bssid !== currentAccesspointBssid) {
				$tr.removeClass("selected-ap");
			} else {
				$tr.addClass("selected-ap");
			}
		});
	};

	const scrollToSelectedAccesspoint = () => {
		if (
			handshakeTarget === null ||
			accesspoints === null ||
			accesspoints === undefined ||
			currentAccesspointBssid === null
		) {
			return;
		}

		if (Object.keys(accesspoints).length === 0) {
			return;
		}

		const bssid = handshakeTarget.bssid;
		const container = $("#networks-display-container");
		const targetRow = container.find(`[data-bssid="${bssid}"]`);

		container.animate({
			scrollTop:
				targetRow.offset().top - container.offset().top + container.scrollTop(),
		});

		toggleTabs(false);
	};

	const startScanning = (isClicked = false) => {
		if (eviltwinTarget && eviltwinTarget.isActive && !eviltwinTarget.isFound) {
			fadingAlert("Eviltwin must be disable to start scanning", 1);
			startScanBtn.trigger("blur");
			return;
		}

		startScanBtn.hide();

		if (isClicked) {
			startScanLoader.show();
		}

		$.ajax({
			type: "POST",
			url: "/accesspoints/start-scan",
		}).done((resp) => {
			if (resp.status !== 1) {
				location.reload();
				return;
			}

			startScanLoader.hide();

			if (resp.status === 1 && !isScanning) {
				isScanning = true;

				startScanBtn.hide();
				stopScanBtn.show();
				disableMonModeBtn.prop("disabled", true);
				refreshOutput.prop("disabled", false);
				startAccesspointScanOutput();
			}
		});
	};

	const stopScanning = () => {
		stopScanBtn.hide();
		stopScanLoader.show();

		$.ajax({
			type: "POST",
			url: "/accesspoints/stop-scan",
		}).done((resp) => {
			stopScanLoader.hide();

			if (resp.status === 1 && isScanning) {
				isScanning = false;

				startScanBtn.show();
				stopScanBtn.hide();

				enableMonModeDisableBtn();
				refreshOutput.prop("disabled", true);
				stopAccesspointScanOutput();
			}
		});
	};

	startScanBtn.on("click", () => {
		startScanning(true);
	});

	stopScanBtn.on("click", () => {
		stopScanning();
	});

	refreshOutput.click(() => {
		if (refreshingOutput) {
			return;
		}

		refreshingOutput = true;

		$.ajax({
			type: "POST",
			url: "/accesspoints/refresh-output",
		}).done((resp) => {
			refreshingOutput = false;
			refreshOutput.blur();
			processAccesspoints(null);
		});
	});

	const toggleTabs = (isClicked = true) => {
		if (isMonitorMode == undefined) {
			return;
		}

		if (!isMonitorMode) {
			// Handshake section
			handshakeTab.addClass("disabled");
			handshakeTab.removeClass("active");
			handshakeSection.removeClass("active");

			// Eviltwin section
			eviltwinTab.addClass("disabled");
			eviltwinTab.removeClass("active");
			eviltwinSection.removeClass("active");

			scanTab.addClass("active");
			scanSection.addClass("active");
		} else {
			if (
				!isClicked &&
				!scanTab.hasClass("active") &&
				!eviltwinTab.hasClass("active")
			) {
				handshakeTab.addClass("active");
				handshakeSection.addClass("active");
			}
			handshakeTab.removeClass("disabled");

			// Eviltwin
			if (handshakeTarget && handshakeTarget.isCaptured) {
				if (currentAccesspointBssid === handshakeTarget.bssid) {
					eviltwinTab.removeClass("disabled");
				} else {
					eviltwinTab.addClass("disabled");
					eviltwinSection.removeClass("active");
					eviltwinTab.removeClass("active");
				}
			} else {
				eviltwinTab.addClass("disabled");
				eviltwinTab.removeClass("active");
				eviltwinSection.removeClass("active");
			}
		}

		if (scanTab.hasClass("disabled")) {
			if (isClicked && !handshakeTab.hasClass("active")) {
				scanTab.addClass("active");
				scanSection.addClass("active");
			}
			scanTab.removeClass("disabled");
		}
	};

	const selectAccesspoint = (bssid, isClicked = true) => {
		currentAccesspointBssid = bssid;
		updateSelectedAccesspointDetails();
		updateSelectedAccesspointClients();
		setSelectedAccesspoint();
		toggleTabs(isClicked);

		if (handshakeOutput !== null) {
			if (handshakeTarget.bssid !== bssid) {
				$("#unmatched-info-alert").show();
			} else {
				$("#unmatched-info-alert").hide();
			}
		}

		toggleCaptureHandshake();
	};

	$(document).on("click", ".bssid.clickable", (e) => {
		selectAccesspoint(e.target.dataset["bssid"]);
	});

	const startAccesspointScanOutput = () => {
		if (accesspointScanOutput !== null) {
			return;
		}

		accesspointScanOutput = new EventSource(accesspointScanOutputURL);
		accesspointScanOutput.addEventListener(
			"message",
			accesspointScanOutputProcessor
		);
	};

	const stopAccesspointScanOutput = () => {
		if (accesspointScanOutput === null) {
			return;
		}

		accesspointScanOutput.removeEventListener(
			"message",
			accesspointScanOutputProcessor
		);
		accesspointScanOutput.close();
		accesspointScanOutput = null;
	};

	const accesspointScanOutputProcessor = (e) => {
		if (!isScanning) {
			return;
		}

		let data = e.data;

		if (data === "finished") {
			return;
		}

		if (!data) {
			return;
		}

		data = JSON.parse(data);

		if (data.status !== 1) {
			return;
		}

		processAccesspoints(data.value);
		updateSelectedAccesspointDetails();
		updateSelectedAccesspointClients();
	};

	// ----------------------- End Accesspoint ----------------------- //

	// ----------------------- Start Handshake ----------------------- //

	const startHandshakeOutput = () => {
		if (handshakeOutput !== null) {
			return;
		}

		$("#handshake-info").show();
		$("#handshake-info__essid").text(handshakeTarget.essid);
		$("#handshake-info__bssid").text(handshakeTarget.bssid.slice(9));

		handshakeOutput = new EventSource(handshakeOutputURL);
		handshakeOutput.addEventListener("message", handshakeOutputProcessor);
	};

	const stopHandshakeOutput = () => {
		if (handshakeOutput === null) {
			return;
		}

		$("#handshake-info").hide();
		$("#unmatched-info-alert").hide();

		handshakeOutput.removeEventListener("message", handshakeOutputProcessor);
		handshakeOutput.close();
		handshakeOutput = null;
	};

	const handshakeOutputProcessor = (e) => {
		if (!isListeningForHandshake) {
			return;
		}

		if (e.data !== "finished") {
			return;
		}

		$.ajax({
			type: "GET",
			url: "/handshake/get-details",
		}).done((resp) => {
			if (resp.status !== 1) {
				return;
			}

			stopHandshake(false);
		});
	};

	const startHandshake = (isClicked = false) => {
		if (eviltwinTarget && eviltwinTarget.isActive && !eviltwinTarget.isFound) {
			fadingAlert("Eviltwin must be disable to start handshake", 1);
			startHandshakeBtn.trigger("blur");
			return;
		}

		if (currentAccesspointBssid === null) {
			return;
		}

		const accesspoint = accesspoints[currentAccesspointBssid];

		startHandshakeBtn.hide();

		if (isClicked) {
			startHandshakeLoader.show();
		}

		$.ajax({
			type: "POST",
			data: {
				bssid: accesspoint["bssid"],
				essid: accesspoint["essid"],
				chann: accesspoint["chann"],
			},
			url: "/handshake/start-process",
		}).done((resp) => {
			startHandshakeLoader.hide();

			if (resp.status !== 1) {
				startHandshakeBtn.show();
				return;
			}

			stopHandshakeBtn.show();
			isListeningForHandshake = true;
			handshakeTarget = resp.value.target;

			disableMonModeBtn.prop("disabled", true);
			startHandshakeOutput();
		});
	};

	const stopHandshake = (isClicked = true) => {
		if (!isListeningForHandshake) {
			return;
		}

		stopHandshakeBtn.hide();

		if (isClicked) {
			stopHandshakeLoader.show();
		}

		$.ajax({
			type: "POST",
			url: "/handshake/stop-process",
		}).done((resp) => {
			stopHandshakeLoader.hide();

			if (resp.status !== 1) {
				stopHandshakeBtn.show();
				return;
			}

			stopHandshakeBtn.hide();
			startHandshakeBtn.show();
			isListeningForHandshake = false;

			enableMonModeDisableBtn();
			stopHandshakeOutput();

			// update local handshake target status
			if (handshakeTarget && handshakeTarget.isActive) {
				$.ajax({
					type: "GET",
					url: "/handshake/status",
				}).done((resp) => {
					if (resp.status === 1) {
						handshakeTarget = resp.value.target;
						handshakeTarget.isCaptured && fadingAlert("Handshake captured", 0);
						toggleTabs((isClicked = false));
						resumeHandshakeState();
						toggleCaptureHandshake();
					}
				});
			}
		});
	};

	const toggleCaptureHandshake = () => {
		const handshakeCaptured = $("#handshake-captured");

		if (
			handshakeTarget &&
			handshakeTarget.isCaptured &&
			handshakeTarget.bssid === currentAccesspointBssid
		) {
			startHandshakeBtn.hide();
			handshakeCaptured.show();
		} else {
			if (
				!handshakeTarget ||
				(handshakeTarget &&
					(!handshakeTarget.isActive || handshakeTarget.isCaptured))
			) {
				startHandshakeBtn.show();
			}
			handshakeCaptured.hide();
		}
	};

	startHandshakeBtn.on("click", () => {
		startHandshake(true);
	});

	stopHandshakeBtn.on("click", () => {
		stopHandshake();
	});

	// ----------------------- End Handshake ----------------------- //

	// ----------------------- Start Eviltwin ----------------------- //

	$(document).on("click", ".captured-ap-bssid.clickable", (e) => {
		loadCapturedAccesspoints(e.target.dataset["bssid"]);
	});

	$(document).on("click", ".remove-captured-accesspoint", (e) => {
		if (!confirm("Are you sure you want to remove this accesspoint?")) {
			loadCapturedAccesspoints();
			return;
		}

		$.ajax({
			type: "POST",
			data: {
				bssid: e.target.dataset["bssid"],
			},
			url: "/eviltwin/remove-captured-ap",
		}).done((resp) => {
			if (resp.status === 1) {
				getCapturedAps();
			}
		});
	});

	const loadCapturedAccesspoints = (selectedBssid = undefined) => {
		$("#captured-aps").text("");

		capturedAccesspoints.forEach((ap) => {
			const bssid = ap.bssid;

			const tr = $("<tr>");

			const btn = $("<button>", {
				"data-bssid": bssid,
				class:
					"remove-captured-accesspoint btn btn-sm btn-danger mr-4 py-0 px-1",
			});

			btn.append($("<i>", { class: "bi bi-trash", "data-bssid": bssid }));

			const bssidSection = $("<span>", {
				"data-bssid": bssid,
				class: "captured-ap-bssid clickable",
			});
			bssidSection.text(bssid);

			tr.append(
				$("<td>")
					.append(
						selectedBssid === bssid &&
							SelectedCapturedAccesspointBssid !== bssid
							? btn
							: ""
					)
					.append(bssidSection)
			);
			tr.append($("<td>").text(ap.essid));
			tr.append($("<td>", { class: "text-success" }).text(ap.passphrase));
			tr.append($("<td>").text(ap.time_captured));
			tr.append($("<td>").text(ap.last_modified));

			$("#captured-aps").append(tr);
		});

		SelectedCapturedAccesspointBssid =
			SelectedCapturedAccesspointBssid !== selectedBssid ? selectedBssid : null;
	};

	const getCapturedAps = () => {
		$.ajax({
			type: "GET",
			url: "/eviltwin/get-captured-aps",
		}).done((resp) => {
			if (resp.status === 1) {
				capturedAccesspoints = resp.value;
				loadCapturedAccesspoints();
			}
		});
	};

	const processEvilTwinClients = (_clients) => {
		$("#eviltwin-clients-display").text("");
		clients = _clients;

		_clients.forEach((client) => {
			const tr = $("<tr>");

			tr.append(
				$("<td>", {
					"data-mac": client.mac,
					class: "mac clickable",
				}).text(client.mac)
			);
			tr.append($("<td>").text(client.ip));
			tr.append($("<td>").text(client.first_seen));
			tr.append($("<td>").text(client.queries.length));

			$("#eviltwin-clients-display").append(tr);
		});

		updateSelectedClientQueries();
	};

	$(document).on("click", ".mac.clickable", (e) => {
		selectClient(e.target.dataset["mac"]);
	});

	const selectClient = (mac, isClicked = true) => {
		currentClientMac = mac;
		updateSelectedClientQueries(isClicked);
	};

	const updateSelectedClientQueries = (isClicked = false) => {
		if (!currentClientMac || clients.length === 0) {
			return;
		}

		let client = clients.find((c) => c.mac === currentClientMac);

		if (!client) {
			return;
		}

		$("#selected-eviltwin-client").text(
			`of ${client.ip ? client.ip : client.mac}`
		);
		$("#eviltwin-queries-display").text("");

		if (client.queries.length && isClicked) {
			$("#evil-twin-display").animate({
				scrollTop: $("#evil-twin-display")[0].scrollHeight,
			});
		}

		client.queries.forEach((query) => {
			const tr = $("<tr>");
			tr.append($("<td>").text(query.link));
			tr.append($("<td>").text(query.date));
			tr.append($("<td>").text(query.time));
			$("#eviltwin-queries-display").append(tr);
		});
	};

	const startEviltwinOutput = () => {
		if (eviltwinOutput !== null) {
			return;
		}

		eviltwinOutput = new EventSource(eviltwinOutputURL);
		eviltwinOutput.addEventListener("message", EviltwinOutputProcessor);
	};

	const stopEviltwinOutput = () => {
		if (eviltwinOutput === null) {
			return;
		}

		eviltwinOutput.removeEventListener("message", EviltwinOutputProcessor);
		eviltwinOutput.close();
		eviltwinOutput = null;

		getCapturedAps();
	};

	const EviltwinOutputProcessor = (e) => {
		if (!isListeningForPassphrase) {
			return;
		}
		let data = e.data;

		if (data === "finished") {
			stopEviltwin(false);
			return;
		}

		data = JSON.parse(data);

		if (!data) {
			return;
		}

		if (data.status !== 1) {
			return;
		}

		if (data.clients !== clients) {
			processEvilTwinClients(data.clients);
		}

		$.ajax({
			type: "GET",
			url: "/eviltwin/status",
		}).done((resp) => {
			if (resp.status !== 1) {
				return;
			}

			eviltwinTarget = resp.value.eviltwin || null;

			if (
				eviltwinTarget &&
				(eviltwinTarget.isFound || !eviltwinTarget.isActive)
			) {
				stopEviltwin(false);
			}
		});
	};

	const startEviltwin = (isClicked = false) => {
		startEviltwinBtn.hide();

		if (isClicked) {
			startEviltwinLoader.show();
		}

		$.ajax({
			type: "POST",
			url: "/eviltwin/start-process",
		}).done((resp) => {
			startEviltwinLoader.hide();

			if (resp.status !== 1) {
				fadingAlert("Failed to start eviltwin", 1);
				startEviltwinBtn.show();
				return;
			}

			fadingAlert("Eviltwin started", 0);
			isListeningForPassphrase = true;

			startEviltwinBtn.hide();
			stopEviltwinBtn.show();

			resumeEviltwinState();
			startEviltwinOutput();
			syncWithServer();
		});
	};

	const stopEviltwin = (isClicked = true) => {
		stopEviltwinBtn.hide();

		if (isClicked) {
			stopEviltwinLoader.show();
		}

		$.ajax({
			type: "POST",
			url: "/eviltwin/stop-process",
		}).done((resp) => {
			stopEviltwinLoader.hide();

			if (resp.status !== 1) {
				stopEviltwinBtn.show();
				return;
			}

			fadingAlert("Eviltwin stop", 0);
			isListeningForPassphrase = false;
			enableMonModeDisableBtn();

			startEviltwinBtn.show();
			stopEviltwinBtn.hide();

			resumeEviltwinState();
			stopEviltwinOutput();
			syncWithServer();
		});
	};

	startEviltwinBtn.on("click", () => {
		startEviltwin(true);
	});

	stopEviltwinBtn.on("click", () => {
		stopEviltwin();
	});

	// ----------------------- End Eviltwin ----------------------- //
})();
