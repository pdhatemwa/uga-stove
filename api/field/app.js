const API_BASE_URL = `${window.location.origin}/api/v1`;
const DATABASE_NAME = "uga-stove-field";
const DATABASE_VERSION = 1;
const SETTINGS_STORE = "settings";
const QUEUE_STORE = "queue";

const loginScreen = document.querySelector("#login-screen");
const fieldScreen = document.querySelector("#field-screen");
const loginForm = document.querySelector("#login-form");
const recordForm = document.querySelector("#record-form");

const loginMessage = document.querySelector("#login-message");
const recordMessage = document.querySelector("#record-message");
const syncMessage = document.querySelector("#sync-message");
const connectionStatus = document.querySelector("#connection-status");

const currentUserName = document.querySelector("#current-user-name");
const pendingCount = document.querySelector("#pending-count");
const pendingRecords = document.querySelector("#pending-records");
const distributionPointSelect = document.querySelector("#distribution-point");

const signatureCanvas = document.querySelector("#signature-canvas");
const signatureArea = document.querySelector("#signature-area");
const thumbprintArea = document.querySelector("#thumbprint-area");
const thumbprintPhoto = document.querySelector("#thumbprint-photo");

let signatureContext = null;
let isDrawing = false;
let hasSignature = false;


function setMessage(element, message = "", type = "") {
    element.textContent = message;
    element.className = `message ${type}`.trim();
}


function normalizeIdentifier(value) {
    return value.trim().toUpperCase().replace(/\s+/g, "");
}


function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);

        request.onupgradeneeded = () => {
            const database = request.result;

            if (!database.objectStoreNames.contains(SETTINGS_STORE)) {
                database.createObjectStore(SETTINGS_STORE);
            }

            if (!database.objectStoreNames.contains(QUEUE_STORE)) {
                database.createObjectStore(QUEUE_STORE, {
                    keyPath: "id",
                });
            }
        };

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}


async function getSetting(key) {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(SETTINGS_STORE, "readonly");
        const request = transaction.objectStore(SETTINGS_STORE).get(key);

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}


async function saveSetting(key, value) {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(SETTINGS_STORE, "readwrite");

        transaction.objectStore(SETTINGS_STORE).put(value, key);
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(transaction.error);
    });
}


async function removeSetting(key) {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(SETTINGS_STORE, "readwrite");

        transaction.objectStore(SETTINGS_STORE).delete(key);
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(transaction.error);
    });
}


async function getQueuedRecords() {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(QUEUE_STORE, "readonly");
        const request = transaction.objectStore(QUEUE_STORE).getAll();

        request.onsuccess = () => {
            const records = request.result.sort(
                (left, right) => left.createdAt.localeCompare(right.createdAt)
            );
            resolve(records);
        };

        request.onerror = () => reject(request.error);
    });
}


async function saveQueuedRecord(record) {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(QUEUE_STORE, "readwrite");

        transaction.objectStore(QUEUE_STORE).put(record);
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(transaction.error);
    });
}


async function deleteQueuedRecord(recordId) {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(QUEUE_STORE, "readwrite");

        transaction.objectStore(QUEUE_STORE).delete(recordId);
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(transaction.error);
    });
}


function getAuthorizationHeaders(token) {
    return {
        Authorization: `Bearer ${token}`,
    };
}


function updateConnectionStatus() {
    const online = navigator.onLine;

    connectionStatus.textContent = online ? "Internet connected" : "Offline";
    connectionStatus.className = `status-pill ${online ? "online" : "offline"}`;
}


function resizeSignatureCanvas() {
    const ratio = Math.max(window.devicePixelRatio || 1, 1);
    const width = signatureCanvas.clientWidth;
    const height = signatureCanvas.clientHeight;

    signatureCanvas.width = width * ratio;
    signatureCanvas.height = height * ratio;

    signatureContext = signatureCanvas.getContext("2d");
    signatureContext.scale(ratio, ratio);
    signatureContext.lineWidth = 3;
    signatureContext.lineCap = "round";
    signatureContext.strokeStyle = "#16221d";
}


function getCanvasPosition(event) {
    const rectangle = signatureCanvas.getBoundingClientRect();

    return {
        x: event.clientX - rectangle.left,
        y: event.clientY - rectangle.top,
    };
}


function startDrawing(event) {
    isDrawing = true;
    hasSignature = true;

    const position = getCanvasPosition(event);

    signatureContext.beginPath();
    signatureContext.moveTo(position.x, position.y);
    signatureCanvas.setPointerCapture(event.pointerId);
}


function drawSignature(event) {
    if (!isDrawing) {
        return;
    }

    const position = getCanvasPosition(event);

    signatureContext.lineTo(position.x, position.y);
    signatureContext.stroke();
}


function stopDrawing() {
    isDrawing = false;
}


function clearSignature() {
    const width = signatureCanvas.clientWidth;
    const height = signatureCanvas.clientHeight;

    signatureContext.clearRect(0, 0, width, height);
    hasSignature = false;
}


function getSelectedEvidenceType() {
    return document.querySelector(
        'input[name="evidence_type"]:checked'
    ).value;
}


function updateEvidenceInput() {
    const evidenceType = getSelectedEvidenceType();

    signatureArea.classList.toggle(
        "hidden",
        evidenceType !== "beneficiary_signature"
    );

    thumbprintArea.classList.toggle(
        "hidden",
        evidenceType !== "thumbprint"
    );
}


function canvasToBlob() {
    return new Promise((resolve) => {
        signatureCanvas.toBlob(resolve, "image/png");
    });
}


function validateRecordFields(formData) {
    const requiredFields = [
        ["household_uid", "Enter the household ID."],
        ["household_head_name", "Enter the family name."],
        ["household_size", "Enter the number of people in the household."],
        ["phone_number", "Enter a mobile number."],
        ["distribution_point_id", "Choose a distribution point."],
        ["stove_size", "Enter the stove type or size."],
        ["serial_number", "Enter the stove serial number."],
        ["distributed_on", "Choose the date given."],
        ["subcounty", "Enter the subcounty."],
        ["parish", "Enter the parish."],
        ["village", "Enter the village."],
        ["receiver_name", "Enter the receiver's name."],
        ["ambassador_name", "Enter the ambassador's name."],
    ];

    for (const [fieldName, message] of requiredFields) {
        if (!String(formData.get(fieldName) || "").trim()) {
            throw new Error(message);
        }
    }

    const householdSize = Number(formData.get("household_size"));

    if (!Number.isInteger(householdSize) || householdSize < 1 || householdSize > 100) {
        throw new Error("Household size must be a whole number from 1 to 100.");
    }

    if (!document.querySelector("#carbon-waiver-accepted").checked) {
        throw new Error("The beneficiary must accept the carbon waiver.");
    }

    if (!document.querySelector("#conditions-accepted").checked) {
        throw new Error("The beneficiary must accept the stove conditions.");
    }
}


function createRecordPayload(formData) {
    validateRecordFields(formData);

    return {
        household_uid: formData.get("household_uid").trim(),
        household_head_name: formData.get("household_head_name").trim(),
        family_name: formData.get("household_head_name").trim(),
        household_size: Number(formData.get("household_size")),
        phone_number: formData.get("phone_number").trim(),
        additional_contact: formData.get("additional_contact").trim() || null,
        district: "Ntungamo",
        subcounty: formData.get("subcounty").trim(),
        parish: formData.get("parish").trim(),
        village: formData.get("village").trim(),
        existing_stove_type_1: null,
        existing_stove_type_2: null,
        fuel_type: null,
        fuel_amount_per_week: null,
        existing_stove_units: null,
        existing_stoves_removed: null,
        serial_number: formData.get("serial_number").trim(),
        stove_type: "Improved Cook Stove",
        stove_size: formData.get("stove_size").trim(),
        distribution_point_id: formData.get("distribution_point_id"),
        distributed_on: formData.get("distributed_on"),
        receiver_type: "Household Head",
        receiver_name: formData.get("receiver_name").trim(),
        receiver_relationship: null,
        carbon_waiver_accepted: true,
        conditions_accepted: true,
        ambassador_name: formData.get("ambassador_name").trim(),
    };
}


async function getEvidence() {
    const evidenceType = getSelectedEvidenceType();

    if (evidenceType === "beneficiary_signature") {
        if (!hasSignature) {
            throw new Error("Ask the beneficiary to sign, or select thumbprint.");
        }

        const blob = await canvasToBlob();

        if (!blob) {
            throw new Error("The signature could not be saved.");
        }

        return {
            method: "beneficiary_signature",
            file: blob,
            filename: "beneficiary-signature.png",
            contentType: "image/png",
        };
    }

    const file = thumbprintPhoto.files[0];

    if (!file) {
        throw new Error("Photograph the beneficiary's thumbprint.");
    }

    return {
        method: "thumbprint",
        file,
        filename: file.name || "beneficiary-thumbprint.jpg",
        contentType: file.type || "image/jpeg",
    };
}


function findLocalDuplicate(records, payload) {
    const householdId = normalizeIdentifier(payload.household_uid);
    const serialNumber = normalizeIdentifier(payload.serial_number);

    return records.find((record) => {
        const queuedPayload = record.payload;

        return (
            normalizeIdentifier(queuedPayload.household_uid) === householdId
            || normalizeIdentifier(queuedPayload.serial_number) === serialNumber
        );
    });
}


async function checkServerDuplicates(payload, token) {
    const parameters = new URLSearchParams({
        household_uid: payload.household_uid,
        serial_number: payload.serial_number,
    });

    const response = await fetch(
        `${API_BASE_URL}/records/check?${parameters.toString()}`,
        {
            headers: getAuthorizationHeaders(token),
        }
    );

    if (!response.ok) {
        return null;
    }

    return response.json();
}


function serverDuplicateMessage(result) {
    if (!result) {
        return null;
    }

    if (result.household_exists) {
        return "Household ID already exists in the central registry.";
    }

    if (result.serial_exists) {
        return "Stove serial number already exists in the central registry.";
    }

    return null;
}


async function loadDistributionPoints(token) {
    const response = await fetch(`${API_BASE_URL}/distribution-points`, {
        headers: getAuthorizationHeaders(token),
    });

    if (!response.ok) {
        throw new Error("Could not load distribution points.");
    }

    const points = await response.json();
    await saveSetting("distributionPoints", points);

    return points;
}


function showDistributionPoints(points, user) {
    distributionPointSelect.innerHTML =
        '<option value="">Choose distribution point</option>';

    const visiblePoints = user.distribution_point_id
        ? points.filter((point) => point.id === user.distribution_point_id)
        : points;

    for (const point of visiblePoints) {
        const option = document.createElement("option");

        option.value = point.id;
        option.textContent = `${point.code}: ${point.name}`;
        distributionPointSelect.appendChild(option);
    }

    if (user.distribution_point_id) {
        distributionPointSelect.value = user.distribution_point_id;
        distributionPointSelect.disabled = true;
    } else {
        distributionPointSelect.disabled = false;
    }
}


async function showFieldScreen() {
    const user = await getSetting("user");
    const points = await getSetting("distributionPoints");

    if (!user) {
        loginScreen.classList.remove("hidden");
        fieldScreen.classList.add("hidden");
        return;
    }

    currentUserName.textContent = user.full_name;
    loginScreen.classList.add("hidden");
    fieldScreen.classList.remove("hidden");

    showDistributionPoints(points || [], user);
    await renderPendingRecords();
}


async function renderPendingRecords() {
    const records = await getQueuedRecords();

    pendingCount.textContent = String(records.length);
    pendingRecords.innerHTML = "";

    if (!records.length) {
        pendingRecords.textContent = "No records are waiting to sync.";
        return;
    }

    for (const record of records) {
        const item = document.createElement("div");

        item.className = `pending-record ${record.status === "conflict" ? "conflict" : ""}`;

        const title = document.createElement("strong");
        title.textContent = `${record.payload.household_uid} | ${record.payload.serial_number}`;

        const detail = document.createElement("span");
        detail.textContent = record.status === "conflict"
            ? `Needs correction: ${record.error}`
            : "Saved on this phone. Waiting for internet connection.";

        item.appendChild(title);
        item.appendChild(detail);
        pendingRecords.appendChild(item);
    }
}


async function login(event) {
    event.preventDefault();
    setMessage(loginMessage);

    if (!navigator.onLine) {
        setMessage(
            loginMessage,
            "Connect to the internet to sign in for the first time.",
            "error"
        );
        return;
    }

    const formData = new FormData(loginForm);
    const body = new URLSearchParams({
        username: formData.get("username"),
        password: formData.get("password"),
    });

    try {
        const loginResponse = await fetch(`${API_BASE_URL}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body,
        });

        if (!loginResponse.ok) {
            throw new Error("Incorrect username or password.");
        }

        const tokenData = await loginResponse.json();

        const userResponse = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: getAuthorizationHeaders(tokenData.access_token),
        });

        if (!userResponse.ok) {
            throw new Error("Could not verify this user account.");
        }

        const user = await userResponse.json();
        const permittedRoles = ["admin", "data_manager", "distribution_officer"];

        if (!permittedRoles.includes(user.role)) {
            throw new Error("This account is not allowed to capture field records.");
        }

        const points = await loadDistributionPoints(tokenData.access_token);

        await saveSetting("token", tokenData.access_token);
        await saveSetting("user", user);
        await saveSetting("distributionPoints", points);

        loginForm.reset();
        setMessage(loginMessage);
        await showFieldScreen();

        if (navigator.onLine) {
            await syncRecords();
        }
    } catch (error) {
        setMessage(loginMessage, error.message, "error");
    }
}


async function saveRecordLocally(event) {
    event.preventDefault();
    setMessage(recordMessage);

    try {
        const formData = new FormData(recordForm);
        const payload = createRecordPayload(formData);
        const evidence = await getEvidence();
        const queuedRecords = await getQueuedRecords();

        const localDuplicate = findLocalDuplicate(queuedRecords, payload);

        if (localDuplicate) {
            throw new Error(
                "Household ID or stove serial number has already been entered on this phone."
            );
        }

        const token = await getSetting("token");

        if (navigator.onLine && token) {
            const duplicateResult = await checkServerDuplicates(payload, token);
            const duplicateMessage = serverDuplicateMessage(duplicateResult);

            if (duplicateMessage) {
                throw new Error(duplicateMessage);
            }
        }

        await saveQueuedRecord({
            id: crypto.randomUUID(),
            createdAt: new Date().toISOString(),
            status: "pending",
            error: null,
            payload,
            evidence,
        });

        recordForm.reset();
        clearSignature();
        thumbprintPhoto.value = "";
        document.querySelector(
            'input[name="evidence_type"][value="beneficiary_signature"]'
        ).checked = true;
        updateEvidenceInput();

        setMessage(
            recordMessage,
            "Record saved on this phone. It will be sent when internet is available.",
            "success"
        );

        await renderPendingRecords();

        if (navigator.onLine) {
            await syncRecords();
        }
    } catch (error) {
        setMessage(recordMessage, error.message, "error");
    }
}


async function sendEvidence(householdId, queuedRecord, token) {
    const evidenceData = new FormData();

    evidenceData.append(
        "evidence",
        queuedRecord.evidence.file,
        queuedRecord.evidence.filename
    );
    evidenceData.append(
        "beneficiary_name",
        queuedRecord.payload.household_head_name
    );
    evidenceData.append(
        "witness_name",
        queuedRecord.payload.ambassador_name
    );
    evidenceData.append("signed_at", new Date().toISOString());
    evidenceData.append("method", queuedRecord.evidence.method);

    const response = await fetch(
        `${API_BASE_URL}/signatures/${encodeURIComponent(householdId)}`,
        {
            method: "POST",
            headers: getAuthorizationHeaders(token),
            body: evidenceData,
        }
    );

    if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.detail || "Could not upload beneficiary evidence.");
    }
}


async function syncQueuedRecord(queuedRecord, token) {
    const duplicateResult = await checkServerDuplicates(queuedRecord.payload, token);
    const duplicateMessage = serverDuplicateMessage(duplicateResult);

    if (duplicateMessage) {
        throw new Error(duplicateMessage);
    }

    const createResponse = await fetch(`${API_BASE_URL}/records`, {
        method: "POST",
        headers: {
            ...getAuthorizationHeaders(token),
            "Content-Type": "application/json",
        },
        body: JSON.stringify(queuedRecord.payload),
    });

    if (!createResponse.ok) {
        const error = await createResponse.json().catch(() => null);
        throw new Error(error?.detail || "Could not save the record to the registry.");
    }

    await sendEvidence(
        queuedRecord.payload.household_uid,
        queuedRecord,
        token
    );
}


async function syncRecords() {
    setMessage(syncMessage);

    if (!navigator.onLine) {
        setMessage(syncMessage, "Internet is not available.", "warning");
        return;
    }

    const token = await getSetting("token");

    if (!token) {
        setMessage(
            syncMessage,
            "Sign in again before sending saved records.",
            "warning"
        );
        return;
    }

    const records = await getQueuedRecords();

    if (!records.length) {
        setMessage(syncMessage, "There are no records waiting to sync.", "success");
        return;
    }

    let sentCount = 0;
    let conflictCount = 0;

    for (const record of records) {
        if (record.status === "conflict") {
            conflictCount += 1;
            continue;
        }

        try {
            await syncQueuedRecord(record, token);
            await deleteQueuedRecord(record.id);
            sentCount += 1;
        } catch (error) {
            record.status = "conflict";
            record.error = error.message;
            await saveQueuedRecord(record);
            conflictCount += 1;
        }
    }

    await renderPendingRecords();

    if (conflictCount) {
        setMessage(
            syncMessage,
            `${sentCount} record(s) sent. ${conflictCount} record(s) need correction before they can be sent.`,
            "warning"
        );
        return;
    }

    setMessage(syncMessage, `${sentCount} record(s) sent successfully.`, "success");
}


async function signOut() {
    await removeSetting("token");
    await removeSetting("user");
    await removeSetting("distributionPoints");

    recordForm.reset();
    clearSignature();
    pendingRecords.innerHTML = "";
    pendingCount.textContent = "0";

    loginScreen.classList.remove("hidden");
    fieldScreen.classList.add("hidden");

    setMessage(
        loginMessage,
        "Signed out. Records already saved on this phone remain available for synchronization after the next sign in.",
        "warning"
    );
}


async function initializeApplication() {
    updateConnectionStatus();
    resizeSignatureCanvas();

    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("./sw.js").catch(() => {
            setMessage(
                loginMessage,
                "Offline application setup failed. Reload while connected to the internet.",
                "warning"
            );
        });
    }

    document.querySelector("#distributed-on").value =
        new Date().toISOString().slice(0, 10);

    await showFieldScreen();

    if (navigator.onLine) {
        await syncRecords();
    }
}


loginForm.addEventListener("submit", login);
recordForm.addEventListener("submit", saveRecordLocally);

document.querySelector("#clear-signature").addEventListener("click", clearSignature);
document.querySelector("#sync-button").addEventListener("click", syncRecords);
document.querySelector("#sign-out-button").addEventListener("click", signOut);

document
    .querySelectorAll('input[name="evidence_type"]')
    .forEach((input) => input.addEventListener("change", updateEvidenceInput));

signatureCanvas.addEventListener("pointerdown", startDrawing);
signatureCanvas.addEventListener("pointermove", drawSignature);
signatureCanvas.addEventListener("pointerup", stopDrawing);
signatureCanvas.addEventListener("pointercancel", stopDrawing);
signatureCanvas.addEventListener("pointerleave", stopDrawing);

window.addEventListener("online", async () => {
    updateConnectionStatus();
    await syncRecords();
});

window.addEventListener("offline", updateConnectionStatus);

window.addEventListener("resize", () => {
    const signatureWasPresent = hasSignature;

    resizeSignatureCanvas();
    hasSignature = signatureWasPresent;
});

initializeApplication();