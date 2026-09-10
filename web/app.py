import csv
import io
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from web.api_client import ApiClient, ApiError

st.set_page_config(page_title="UGA Stove", page_icon="🔥", layout="wide")
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.4rem; padding-bottom: 3rem;}
      [data-testid="stMetric"] {
        background: #f6f8fb; border: 1px solid #dce3ea;
        padding: 1rem; border-radius: .6rem;
      }
      .status-box {
        padding: .8rem 1rem; border-radius: .5rem;
        background: #eef5fb; border-left: 5px solid #2f75b5;
      }
      .small-muted {color: #5f6b7a; font-size: .88rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def api() -> ApiClient:
    return ApiClient(st.session_state.get("access_token"))


def handle_error(exc: ApiError) -> None:
    if exc.status_code == 401:
        st.session_state.clear()
        st.error("Your session has expired. Sign in again.")
        st.rerun()
    st.error(exc.message)


def login_page() -> None:
    left, center, right = st.columns([1, 1.3, 1])
    with center:
        st.title("🔥 UGA Stove")
        st.caption("Secure stove distribution registry for Ntungamo")
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")
        if submitted:
            try:
                result = ApiClient().login(username, password)
                st.session_state.access_token = result["access_token"]
                st.session_state.user = ApiClient(result["access_token"]).get("/api/v1/auth/me")
                st.rerun()
            except ApiError as exc:
                st.error(exc.message)


def dashboard_page() -> None:
    st.header("Live distribution dashboard")
    try:
        data = api().get("/api/v1/dashboard/summary")
    except ApiError as exc:
        handle_error(exc)
        return
    cols = st.columns(5)
    cols[0].metric("Households served", f"{data['unique_households']:,}")
    cols[1].metric("Stoves issued", f"{data['unique_stoves']:,}")
    cols[2].metric(
        "Signed evidence", f"{data['captured_signatures'] + data['verified_signatures']:,}"
    )
    cols[3].metric("Verified", f"{data['verified_signatures']:,}")
    cols[4].metric("Awaiting signature", f"{data['unsigned_records']:,}")

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Progress by distribution point")
        points = pd.DataFrame(data["by_distribution_point"])
        if points.empty:
            st.info("No distributions have been recorded yet.")
        else:
            points = points.rename(
                columns={
                    "distribution_point": "Distribution point",
                    "total": "Total",
                    "signed": "Captured",
                    "verified": "Verified",
                }
            )
            st.dataframe(points, hide_index=True, use_container_width=True)
            st.bar_chart(points.set_index("Distribution point")[["Total", "Captured", "Verified"]])
    with right:
        st.subheader("Stoves by size")
        sizes = pd.DataFrame(
            {
                "Size": ["Large", "Medium", "Small"],
                "Count": [data["large_stoves"], data["medium_stoves"], data["small_stoves"]],
            }
        ).set_index("Size")
        st.bar_chart(sizes)

    st.subheader("Distribution activity over time")
    activity = pd.DataFrame(data["by_date"])
    if not activity.empty:
        activity["date"] = pd.to_datetime(activity["date"])
        st.line_chart(activity.set_index("date")["total"])


def point_options() -> tuple[list[dict], dict[str, str]]:
    points = api().get("/api/v1/distribution-points")
    labels = {f"{point['name']} ({point['code']})": point["id"] for point in points}
    return points, labels


def new_record_page() -> None:
    st.header("Register a stove distribution")
    st.caption("Identifiers are compared without case, spaces, hyphens, or underscores.")
    try:
        points, labels = point_options()
    except ApiError as exc:
        handle_error(exc)
        return
    if not points:
        st.warning("An administrator must create the official distribution points first.")
        return

    check_left, check_right, check_button = st.columns([1, 1, 0.45])
    household_check = check_left.text_input("Household ID to check", key="check_household")
    serial_check = check_right.text_input("Stove serial number to check", key="check_serial")
    if check_button.button("Check", use_container_width=True):
        try:
            result = api().get(
                "/api/v1/records/check",
                params={"household_uid": household_check, "serial_number": serial_check},
            )
            if result["message"]:
                st.error(result["message"])
            else:
                st.success("Both identifiers are available.")
        except ApiError as exc:
            handle_error(exc)

    with st.form("new_record", clear_on_submit=False):
        st.subheader("Household data")
        c1, c2, c3 = st.columns(3)
        household_uid = c1.text_input("Household unique ID *")
        head_name = c2.text_input("Name of household head *")
        household_size = c3.number_input(
            "Number of household members *", min_value=1, max_value=100, value=5
        )
        c1, c2, c3 = st.columns(3)
        phone = c1.text_input("Mobile number *")
        additional_contact = c2.text_input("Additional contact information")
        family_name = c3.text_input("Family name, if different")

        st.subheader("Location")
        c1, c2, c3, c4 = st.columns(4)
        district = c1.text_input("District", value="Ntungamo")
        subcounty = c2.text_input("Subcounty *")
        parish = c3.text_input("Parish *")
        village = c4.text_input("Village *")
        c1, c2, c3 = st.columns(3)
        latitude = c1.number_input("Latitude", value=None, format="%.7f")
        longitude = c2.number_input("Longitude", value=None, format="%.7f")
        gps_precision = c3.number_input("GPS precision in meters", value=None, min_value=0.0)

        st.subheader("Current cooking data")
        c1, c2, c3, c4 = st.columns(4)
        existing_stove = c1.text_input("Existing stove type")
        fuel_type = c2.selectbox("Fuel type", ["", "Firewood", "Charcoal", "Other"])
        existing_units = c3.number_input(
            "Number of existing stove units", min_value=0, max_value=20, value=0
        )
        fuel_week = c4.text_input("Amount of fuel used per week")
        removed = st.selectbox("Existing stove removed", ["Not recorded", "Yes", "No"])

        st.subheader("New improved cook stove")
        c1, c2, c3, c4 = st.columns(4)
        serial = c1.text_input("Stove serial number *")
        stove_size = c2.selectbox("Stove size *", ["Medium", "Large", "Small"])
        distributed_on = c3.date_input("Date of distribution *", value=date.today())
        point_label = c4.selectbox("Distribution point *", list(labels))
        c1, c2, c3 = st.columns(3)
        receiver_type = c1.selectbox("Stove received by *", ["Household Head", "Representative"])
        receiver_name = c2.text_input("Name of receiver")
        relationship = c3.text_input("Relationship to household head")
        ambassador = st.text_input("Ambassador or field officer name *")

        st.subheader("Beneficiary confirmations")
        waiver = st.checkbox("The beneficiary accepted the carbon emission waiver.")
        conditions = st.checkbox("The beneficiary accepted the stove use and return conditions.")
        submitted = st.form_submit_button(
            "Save distribution", type="primary", use_container_width=True
        )

    if submitted:
        payload = {
            "household_uid": household_uid,
            "household_head_name": head_name,
            "family_name": family_name or None,
            "household_size": household_size,
            "phone_number": phone,
            "additional_contact": additional_contact or None,
            "district": district,
            "subcounty": subcounty,
            "parish": parish,
            "village": village,
            "latitude": latitude,
            "longitude": longitude,
            "gps_precision_m": gps_precision,
            "existing_stove_type_1": existing_stove or None,
            "fuel_type": fuel_type or None,
            "fuel_amount_per_week": fuel_week or None,
            "existing_stove_units": existing_units,
            "existing_stoves_removed": None if removed == "Not recorded" else removed == "Yes",
            "serial_number": serial,
            "stove_size": stove_size,
            "distribution_point_id": labels[point_label],
            "distributed_on": distributed_on.isoformat(),
            "receiver_type": receiver_type,
            "receiver_name": receiver_name or None,
            "receiver_relationship": relationship or None,
            "carbon_waiver_accepted": waiver,
            "conditions_accepted": conditions,
            "ambassador_name": ambassador,
        }
        try:
            result = api().post("/api/v1/records", json=payload)
            st.success(
                f"Saved {result['household']['household_uid']}. "
                f"Verification code: {result['verification_code']}"
            )
            st.session_state.last_household_uid = result["household"]["household_uid"]
        except ApiError as exc:
            handle_error(exc)


def _record_summary(record: dict) -> None:
    h = record["household"]
    s = record["stove"]
    st.markdown(
        f"<div class='status-box'><b>{h['household_uid']}</b> · {h['household_head_name']} · "
        f"{s['serial_number']} · Signature: {record['signature_status'].title()}</div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Household members", h["household_size"])
    c2.metric("Stove size", s["stove_size"])
    c3.metric("Distribution point", record["distribution_point"]["name"])
    c4.metric("Date", record["distributed_on"])
    with st.expander("View all household and distribution details", expanded=True):
        left, right = st.columns(2)
        left.write(
            {
                "Household head": h["household_head_name"],
                "Phone": h["phone_number"],
                "Location": f"{h['village']}, {h['parish']}, {h['subcounty']}, {h['district']}",
                "Fuel type": h["fuel_type"],
                "Fuel per week": h["fuel_amount_per_week"],
            }
        )
        right.write(
            {
                "Serial number": s["serial_number"],
                "Stove type": s["stove_type"],
                "Receiver": record["receiver_name"] or record["receiver_type"],
                "Ambassador": record["ambassador_name"],
                "Verification code": record["verification_code"],
            }
        )


def lookup_record(default_uid: str = "") -> dict | None:
    uid = st.text_input("Enter household unique ID", value=default_uid)
    if st.button("Retrieve household", type="primary") or (
        uid and st.session_state.get("auto_lookup")
    ):
        st.session_state.auto_lookup = False
        try:
            record = api().get(f"/api/v1/records/{uid}")
            st.session_state.current_record = record
        except ApiError as exc:
            st.session_state.current_record = None
            handle_error(exc)
    return st.session_state.get("current_record")


def search_print_page() -> None:
    st.header("Find household and print forms")
    record = lookup_record(st.session_state.pop("last_household_uid", ""))
    if not record:
        return
    _record_summary(record)
    try:
        pdf = api().get(
            f"/api/v1/records/{record['household']['household_uid']}/form.pdf", raw=True
        )
        st.download_button(
            "Download and print participation form plus certificate",
            data=pdf,
            file_name=f"UGA-Stove-{record['household']['household_uid']}.pdf",
            mime="application/pdf",
            type="primary",
        )
    except ApiError as exc:
        handle_error(exc)

    evidence_items = record.get("signature_evidence", [])
    if evidence_items:
        st.subheader("Signature evidence")
        evidence_table = pd.DataFrame(evidence_items)[
            ["beneficiary_name", "witness_name", "signed_at", "sha256", "verified_at"]
        ]
        st.dataframe(evidence_table, hide_index=True, use_container_width=True)
        choices = {
            f"{item['signed_at']} · {item['original_filename']}": item for item in evidence_items
        }
        selected_label = st.selectbox("Evidence file", list(choices))
        selected = choices[selected_label]
        try:
            evidence_file = api().get(
                f"/api/v1/signatures/evidence/{selected['id']}/file", raw=True
            )
            st.download_button(
                "Download evidence file",
                data=evidence_file,
                file_name=selected["original_filename"],
            )
        except ApiError as exc:
            handle_error(exc)

        if st.session_state.user["role"] in {"admin", "data_manager"}:
            review_reason = st.text_input("Review note or rejection reason")
            approve, reject = st.columns(2)
            if approve.button("Verify this evidence", type="primary", use_container_width=True):
                try:
                    updated = api().post(
                        f"/api/v1/signatures/evidence/{selected['id']}/review",
                        json={"approve": True, "reason": review_reason or None},
                    )
                    st.session_state.current_record = updated
                    st.success("Signature evidence verified.")
                    st.rerun()
                except ApiError as exc:
                    handle_error(exc)
            if reject.button("Reject this evidence", use_container_width=True):
                try:
                    updated = api().post(
                        f"/api/v1/signatures/evidence/{selected['id']}/review",
                        json={"approve": False, "reason": review_reason or None},
                    )
                    st.session_state.current_record = updated
                    st.warning("Signature evidence rejected for correction.")
                    st.rerun()
                except ApiError as exc:
                    handle_error(exc)


def signature_page() -> None:
    st.header("Record physical signature evidence")
    st.info(
        "Print the form, let the beneficiary sign it, then photograph or scan the signed page. "
        "This records evidence of a physical signature. It is not presented as a "
        "cryptographic digital signature."
    )
    record = lookup_record()
    if not record:
        return
    _record_summary(record)
    source = st.radio("Evidence source", ["Use phone or computer camera", "Upload a scan or photo"])
    if source.startswith("Use"):
        evidence = st.camera_input("Photograph the signed page", resolution="720p")
    else:
        evidence = st.file_uploader("Upload signed evidence", type=["jpg", "jpeg", "png", "pdf"])
    c1, c2 = st.columns(2)
    beneficiary_name = c1.text_input(
        "Name of beneficiary who signed", value=record["household"]["household_head_name"]
    )
    witness_name = c2.text_input("Witness or ambassador name", value=record["ambassador_name"])
    c1, c2 = st.columns(2)
    signed_date = c1.date_input("Date signed", value=date.today())
    signed_time = c2.time_input(
        "Time signed", value=datetime.now().time().replace(second=0, microsecond=0)
    )
    notes = st.text_area("Notes")
    if st.button("Record signature evidence", type="primary", disabled=evidence is None):
        signed_at = datetime.combine(
            signed_date, signed_time, tzinfo=ZoneInfo("Africa/Kampala")
        ).isoformat()
        files = {
            "evidence": (
                evidence.name,
                evidence.getvalue(),
                evidence.type or "application/octet-stream",
            )
        }
        data = {
            "beneficiary_name": beneficiary_name,
            "witness_name": witness_name,
            "signed_at": signed_at,
            "notes": notes,
        }
        try:
            result = api().post(
                f"/api/v1/signatures/{record['household']['household_uid']}",
                data=data,
                files=files,
            )
            st.session_state.current_record = result
            st.success("Signature evidence captured with a timestamp and tamper evident file hash.")
        except ApiError as exc:
            handle_error(exc)


def corrections_page() -> None:
    st.header("Correct an existing record")
    record = lookup_record()
    if not record:
        return
    _record_summary(record)
    h, s = record["household"], record["stove"]
    privileged = st.session_state.user["role"] in {"admin", "data_manager"}
    with st.form("correction"):
        c1, c2 = st.columns(2)
        new_uid = c1.text_input("Household ID", value=h["household_uid"], disabled=not privileged)
        new_serial = c2.text_input(
            "Stove serial number", value=s["serial_number"], disabled=not privileged
        )
        c1, c2, c3 = st.columns(3)
        head = c1.text_input("Household head", value=h["household_head_name"])
        phone = c2.text_input("Phone", value=h["phone_number"])
        size = c3.number_input(
            "Household members", min_value=1, max_value=100, value=h["household_size"]
        )
        c1, c2, c3 = st.columns(3)
        subcounty = c1.text_input("Subcounty", value=h["subcounty"])
        parish = c2.text_input("Parish", value=h["parish"])
        village = c3.text_input("Village", value=h["village"])
        reason = st.text_area("Reason for correction *", help="This is written to the audit trail.")
        submitted = st.form_submit_button("Save correction", type="primary")
    if submitted:
        payload = {
            "expected_version": record["row_version"],
            "reason": reason,
            "household_head_name": head,
            "phone_number": phone,
            "household_size": size,
            "subcounty": subcounty,
            "parish": parish,
            "village": village,
        }
        if privileged:
            payload.update({"household_uid": new_uid, "serial_number": new_serial})
        try:
            updated = api().patch(f"/api/v1/records/{h['household_uid']}", payload)
            st.session_state.current_record = updated
            st.success(
                "Record corrected. The previous and new values are preserved in the audit log."
            )
        except ApiError as exc:
            handle_error(exc)


def _rejects_csv(result: dict) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=["row_number", "household_uid", "serial_number", "reason"]
    )
    writer.writeheader()
    writer.writerows(result.get("rejects", []))
    return output.getvalue().encode("utf-8-sig")


def admin_page() -> None:
    st.header("Management and assurance")
    role = st.session_state.user["role"]
    tab_names = []
    if role == "admin":
        tab_names.extend(["Distribution points", "Users"])
    if role in {"admin", "data_manager"}:
        tab_names.append("Kobo migration")
    if role in {"admin", "data_manager", "auditor"}:
        tab_names.append("Audit log")
    tabs = dict(zip(tab_names, st.tabs(tab_names), strict=True))

    if "Distribution points" in tabs:
        with tabs["Distribution points"]:
            st.subheader("Create an official distribution point")
            with st.form("create_point"):
                code = st.text_input("Short code", placeholder="POINT-1")
                name = st.text_input("Official name")
                create = st.form_submit_button("Create point")
            if create:
                try:
                    api().post(
                        "/api/v1/admin/distribution-points", json={"code": code, "name": name}
                    )
                    st.success("Distribution point created.")
                except ApiError as exc:
                    handle_error(exc)

    if "Users" in tabs:
        with tabs["Users"]:
            try:
                _, labels = point_options()
            except ApiError:
                labels = {}
            with st.form("create_user"):
                c1, c2 = st.columns(2)
                username = c1.text_input("Username")
                full_name = c2.text_input("Full name")
                c1, c2 = st.columns(2)
                password = c1.text_input("Temporary password", type="password")
                new_role = c2.selectbox(
                    "Role",
                    [
                        "distribution_officer",
                        "data_manager",
                        "auditor",
                        "stakeholder",
                        "admin",
                    ],
                )
                assigned = st.selectbox("Assigned point", ["Not assigned", *labels])
                create = st.form_submit_button("Create user")
            if create:
                try:
                    api().post(
                        "/api/v1/admin/users",
                        json={
                            "username": username,
                            "full_name": full_name,
                            "password": password,
                            "role": new_role,
                            "distribution_point_id": None
                            if assigned == "Not assigned"
                            else labels[assigned],
                        },
                    )
                    st.success("User created.")
                except ApiError as exc:
                    handle_error(exc)

    if "Kobo migration" in tabs:
        with tabs["Kobo migration"]:
            st.subheader("Controlled Kobo CSV migration")
            st.caption(
                "Run a dry check first. Duplicates and unmapped locations are quarantined, "
                "not guessed."
            )
            source = st.file_uploader(
                "Kobo semicolon separated export", type=["csv", "txt"], key="source"
            )
            mapping = st.file_uploader(
                "Distribution point mapping CSV", type=["csv"], key="mapping"
            )
            commit = st.checkbox("Commit valid rows after validation")
            if st.button("Run import analysis", disabled=not source or not mapping):
                try:
                    result = api().post(
                        "/api/v1/admin/imports/kobo",
                        data={"commit": str(commit).lower()},
                        files={
                            "source": (source.name, source.getvalue(), "text/csv"),
                            "point_mapping": (mapping.name, mapping.getvalue(), "text/csv"),
                        },
                    )
                    st.session_state.import_result = result
                except ApiError as exc:
                    handle_error(exc)
            result = st.session_state.get("import_result")
            if result:
                c1, c2, c3 = st.columns(3)
                c1.metric("Rows", result["total_rows"])
                c2.metric("Inserted", result["inserted_rows"])
                c3.metric("Rejected", result["rejected_rows"])
                if result["unknown_distribution_labels"]:
                    st.warning(
                        "Unmapped labels: " + ", ".join(result["unknown_distribution_labels"][:20])
                    )
                if result["rejects"]:
                    st.download_button(
                        "Download rejected rows report",
                        data=_rejects_csv(result),
                        file_name="uga_stove_import_rejects.csv",
                        mime="text/csv",
                    )

    if "Audit log" in tabs:
        with tabs["Audit log"]:
            try:
                logs = api().get("/api/v1/admin/audit", params={"limit": 300})
                st.dataframe(pd.DataFrame(logs), hide_index=True, use_container_width=True)
            except ApiError as exc:
                handle_error(exc)


def main() -> None:
    if "access_token" not in st.session_state:
        login_page()
        return
    if "user" not in st.session_state:
        try:
            st.session_state.user = api().get("/api/v1/auth/me")
        except ApiError as exc:
            handle_error(exc)
            return
    user = st.session_state.user
    with st.sidebar:
        st.title("🔥 UGA Stove")
        st.write(user["full_name"])
        st.caption(user["role"].replace("_", " ").title())
        pages = ["Dashboard"]
        if user["role"] != "stakeholder":
            pages.extend(["Find and print"])
        if user["role"] in {"admin", "data_manager", "distribution_officer"}:
            pages.extend(["New distribution", "Record signature", "Correct record"])
        if user["role"] in {"admin", "data_manager", "auditor"}:
            pages.append("Management")
        page = st.radio("Navigation", pages, label_visibility="collapsed")
        with st.expander("Change password"):
            with st.form("change_password"):
                current_password = st.text_input("Current password", type="password")
                new_password = st.text_input("New password", type="password")
                change_password = st.form_submit_button("Change password")
            if change_password:
                try:
                    api().post(
                        "/api/v1/auth/change-password",
                        json={
                            "current_password": current_password,
                            "new_password": new_password,
                        },
                    )
                    st.session_state.clear()
                    st.success("Password changed. Sign in again.")
                    st.rerun()
                except ApiError as exc:
                    handle_error(exc)
        if st.button("Sign out", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    if page == "Dashboard":
        dashboard_page()
    elif page == "New distribution":
        new_record_page()
    elif page == "Find and print":
        search_print_page()
    elif page == "Record signature":
        signature_page()
    elif page == "Correct record":
        corrections_page()
    elif page == "Management":
        admin_page()


if __name__ == "__main__":
    main()
