"""
Unit tests for new multi-phone/email/org features in Google Contacts tools.

Covers:
- _build_person_body with phones/emails/organizations lists
- Deprecated aliases with warnings
- _merge_phones / _merge_emails / _merge_organizations
- _format_contact with typed phones/emails (multi-line output)
- _format_phone_line / _format_email_line
- Batch update: field param validation, contacts_map (dict not list)
- Internal PBX type
"""

import sys
import os
import warnings

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gcontacts.contacts_tools import (
    _format_contact,
    _format_phone_line,
    _format_email_line,
    _build_person_body,
    _merge_phones,
    _merge_emails,
    _merge_organizations,
    _normalize_phone,
    _normalize_email,
)


# =============================================================================
# _normalize helpers
# =============================================================================

class TestNormalize:
    def test_normalize_phone_strips_parens_dashes(self):
        assert _normalize_phone("+7 (927) 000-00-00") == "+79270000000"

    def test_normalize_phone_e164(self):
        assert _normalize_phone("+79270000000") == "+79270000000"

    def test_normalize_phone_short_internal(self):
        assert _normalize_phone("250") == "250"

    def test_normalize_email_lowercase(self):
        assert _normalize_email("  User@Example.COM  ") == "user@example.com"


# =============================================================================
# _format_phone_line
# =============================================================================

class TestFormatPhoneLine:
    def test_phone_with_type(self):
        phone = {"value": "+79270000000", "type": "mobile"}
        assert _format_phone_line(phone) == "+79270000000 (mobile)"

    def test_phone_with_formatted_type(self):
        phone = {"value": "+79270000000", "type": "mobile", "formattedType": "Mobile"}
        assert _format_phone_line(phone) == "+79270000000 (Mobile)"

    def test_phone_internal_type(self):
        phone = {"value": "250", "type": "internal"}
        assert _format_phone_line(phone) == "250 (Internal)"

    def test_phone_no_type(self):
        phone = {"value": "+79270000000"}
        assert _format_phone_line(phone) == "+79270000000"

    def test_phone_empty_type(self):
        phone = {"value": "+79270000000", "type": ""}
        assert _format_phone_line(phone) == "+79270000000"


# =============================================================================
# _format_email_line
# =============================================================================

class TestFormatEmailLine:
    def test_email_with_type(self):
        email = {"value": "user@example.com", "type": "work"}
        assert _format_email_line(email) == "user@example.com (work)"

    def test_email_with_formatted_type(self):
        email = {"value": "user@example.com", "type": "work", "formattedType": "Work"}
        assert _format_email_line(email) == "user@example.com (Work)"

    def test_email_no_type(self):
        email = {"value": "user@example.com"}
        assert _format_email_line(email) == "user@example.com"


# =============================================================================
# _format_contact — phones/emails multi-line display
# =============================================================================

class TestFormatContactPhones:
    def test_single_phone_shows_inline(self):
        person = {
            "resourceName": "people/c1",
            "phoneNumbers": [{"value": "+79270000000", "type": "mobile"}],
        }
        result = _format_contact(person)
        assert "Phone: +79270000000 (mobile)" in result
        assert "Phones:" not in result

    def test_multiple_phones_show_block(self):
        person = {
            "resourceName": "people/c1",
            "phoneNumbers": [
                {"value": "+79270000000", "type": "mobile"},
                {"value": "+78482123456", "type": "work"},
                {"value": "250", "type": "internal"},
            ],
        }
        result = _format_contact(person)
        assert "Phones:" in result
        assert "  - +79270000000 (mobile)" in result
        assert "  - +78482123456 (work)" in result
        assert "  - 250 (Internal)" in result

    def test_single_email_shows_inline(self):
        person = {
            "resourceName": "people/c1",
            "emailAddresses": [{"value": "user@work.com", "type": "work"}],
        }
        result = _format_contact(person)
        assert "Email: user@work.com (work)" in result
        assert "Emails:" not in result

    def test_multiple_emails_show_block(self):
        person = {
            "resourceName": "people/c1",
            "emailAddresses": [
                {"value": "work@example.com", "type": "work"},
                {"value": "personal@example.com", "type": "home"},
            ],
        }
        result = _format_contact(person)
        assert "Emails:" in result
        assert "  - work@example.com (work)" in result
        assert "  - personal@example.com (home)" in result

    def test_internal_phone_shows_capital_internal(self):
        person = {
            "resourceName": "people/c1",
            "phoneNumbers": [{"value": "250", "type": "internal"}],
        }
        result = _format_contact(person)
        assert "Phone: 250 (Internal)" in result

    def test_phone_without_type_shows_value_only(self):
        person = {
            "resourceName": "people/c1",
            "phoneNumbers": [{"value": "+79270000000"}],
        }
        result = _format_contact(person)
        assert "Phone: +79270000000" in result


# =============================================================================
# _build_person_body — new phones/emails/organizations params
# =============================================================================

class TestBuildPersonBodyNew:
    def test_phones_list(self):
        body = _build_person_body(
            phones=[
                {"number": "+79270000000", "type": "mobile"},
                {"number": "+78482123456", "type": "work"},
            ]
        )
        assert len(body["phoneNumbers"]) == 2
        assert body["phoneNumbers"][0] == {"value": "+79270000000", "type": "mobile"}
        assert body["phoneNumbers"][1] == {"value": "+78482123456", "type": "work"}

    def test_phones_with_label(self):
        body = _build_person_body(
            phones=[{"number": "250", "type": "internal", "label": "АТС Greenline"}]
        )
        assert body["phoneNumbers"][0] == {
            "value": "250",
            "type": "internal",
            "label": "АТС Greenline",
        }

    def test_emails_list(self):
        body = _build_person_body(
            emails=[
                {"address": "work@example.com", "type": "work"},
                {"address": "personal@example.com", "type": "home"},
            ]
        )
        assert len(body["emailAddresses"]) == 2
        assert body["emailAddresses"][0] == {"value": "work@example.com", "type": "work"}

    def test_organizations_list(self):
        body = _build_person_body(
            organizations=[
                {"name": "Greenline LLC", "title": "Director", "type": "work"},
            ]
        )
        assert body["organizations"][0] == {
            "name": "Greenline LLC",
            "title": "Director",
            "type": "work",
        }

    def test_organizations_with_department(self):
        body = _build_person_body(
            organizations=[{"name": "Acme", "department": "Engineering"}]
        )
        assert body["organizations"][0]["department"] == "Engineering"

    def test_phones_empty_number_skipped(self):
        body = _build_person_body(
            phones=[{"number": "", "type": "mobile"}, {"number": "+79270000000", "type": "work"}]
        )
        assert len(body["phoneNumbers"]) == 1
        assert body["phoneNumbers"][0]["value"] == "+79270000000"

    def test_phones_value_key_fallback(self):
        """phones entries with 'value' key instead of 'number' still work."""
        body = _build_person_body(
            phones=[{"value": "+79270000000", "type": "mobile"}]
        )
        assert body["phoneNumbers"][0]["value"] == "+79270000000"

    def test_emails_value_key_fallback(self):
        """emails entries with 'value' key instead of 'address' still work."""
        body = _build_person_body(
            emails=[{"value": "user@example.com", "type": "work"}]
        )
        assert body["emailAddresses"][0]["value"] == "user@example.com"

    def test_phones_wins_over_deprecated_phone(self):
        """When both phones and phone provided, phone alias ignored with warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            body = _build_person_body(
                phones=[{"number": "+79270000000", "type": "mobile"}],
                phone="+70000000000",
            )
            assert any("ignored" in str(warning.message) for warning in w)
        # Only phones list should be used
        assert len(body["phoneNumbers"]) == 1
        assert body["phoneNumbers"][0]["value"] == "+79270000000"

    def test_emails_wins_over_deprecated_email(self):
        """When both emails and email provided, email alias ignored with warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            body = _build_person_body(
                emails=[{"address": "new@example.com", "type": "work"}],
                email="old@example.com",
            )
            assert any("ignored" in str(warning.message) for warning in w)
        assert len(body["emailAddresses"]) == 1
        assert body["emailAddresses"][0]["value"] == "new@example.com"

    def test_organizations_wins_over_deprecated_aliases(self):
        """When both organizations and organization/job_title provided, aliases ignored."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            body = _build_person_body(
                organizations=[{"name": "NewCorp", "type": "work"}],
                organization="OldCorp",
                job_title="OldTitle",
            )
            assert any("ignored" in str(warning.message) for warning in w)
        assert len(body["organizations"]) == 1
        assert body["organizations"][0]["name"] == "NewCorp"

    def test_internal_phone_no_type_default_not_added(self):
        """phones without type field do not get a default type injected."""
        body = _build_person_body(
            phones=[{"number": "+79270000000"}]
        )
        assert "type" not in body["phoneNumbers"][0]

    def test_all_new_fields_together(self):
        body = _build_person_body(
            given_name="Ivan",
            family_name="Petrov",
            phones=[
                {"number": "+79270000000", "type": "mobile"},
                {"number": "250", "type": "internal"},
            ],
            emails=[{"address": "ivan@example.com", "type": "work"}],
            organizations=[{"name": "Greenline", "title": "CTO"}],
            notes="Key contact",
            address="Moscow, Russia",
        )
        assert body["names"][0]["givenName"] == "Ivan"
        assert len(body["phoneNumbers"]) == 2
        assert body["phoneNumbers"][1] == {"value": "250", "type": "internal"}
        assert body["emailAddresses"][0]["value"] == "ivan@example.com"
        assert body["organizations"][0]["name"] == "Greenline"
        assert body["biographies"][0]["value"] == "Key contact"
        assert body["addresses"][0]["formattedValue"] == "Moscow, Russia"


# =============================================================================
# Deprecated aliases — emit DeprecationWarning, result is correct
# =============================================================================

class TestDeprecatedAliases:
    def test_phone_alias_emits_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            body = _build_person_body(phone="+79270000000")
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "phone" in str(w[0].message).lower()
        assert body["phoneNumbers"][0]["value"] == "+79270000000"
        assert body["phoneNumbers"][0]["type"] == "mobile"

    def test_email_alias_emits_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            body = _build_person_body(email="user@example.com")
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
        assert body["emailAddresses"][0]["value"] == "user@example.com"
        assert body["emailAddresses"][0]["type"] == "other"

    def test_organization_alias_emits_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            body = _build_person_body(organization="Acme Corp")
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
        assert body["organizations"][0]["name"] == "Acme Corp"

    def test_job_title_alias_emits_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            body = _build_person_body(job_title="CEO")
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
        assert body["organizations"][0]["title"] == "CEO"

    def test_phone_and_email_aliases_together(self):
        """Deprecated phone+email together still work as expected."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            body = _build_person_body(phone="+79270000000", email="user@example.com")
        assert body["phoneNumbers"][0]["value"] == "+79270000000"
        assert body["emailAddresses"][0]["value"] == "user@example.com"

    def test_org_and_job_title_aliases_together(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            body = _build_person_body(organization="Acme", job_title="CEO")
        assert body["organizations"][0]["name"] == "Acme"
        assert body["organizations"][0]["title"] == "CEO"


# =============================================================================
# _merge_phones
# =============================================================================

class TestMergePhones:
    def test_merge_adds_new_phone(self):
        existing = [{"value": "+79270000000", "type": "mobile"}]
        new = [{"value": "+78482123456", "type": "work"}]
        result = _merge_phones(existing, new, "merge")
        assert len(result) == 2
        values = [p["value"] for p in result]
        assert "+79270000000" in values
        assert "+78482123456" in values

    def test_merge_deduplicates_by_normalized(self):
        existing = [{"value": "+7 (927) 000-00-00", "type": "mobile"}]
        new = [{"value": "+79270000000", "type": "mobile"}]
        result = _merge_phones(existing, new, "merge")
        # Should remain 1 because they normalize to the same value
        assert len(result) == 1

    def test_merge_deduplicates_by_canonical_form(self):
        existing = [{"value": "+79270000000", "canonicalForm": "+79270000000", "type": "mobile"}]
        new = [{"value": "+7 927 000-00-00", "canonicalForm": "+79270000000", "type": "work"}]
        result = _merge_phones(existing, new, "merge")
        assert len(result) == 1

    def test_merge_keeps_internal_short_number(self):
        """Short internal numbers dedup by normalized value "250"."""
        existing = [{"value": "250", "type": "internal"}]
        new = [{"value": "250", "type": "internal"}]
        result = _merge_phones(existing, new, "merge")
        assert len(result) == 1

    def test_merge_internal_different_from_mobile(self):
        existing = [{"value": "+79270000000", "type": "mobile"}]
        new = [{"value": "250", "type": "internal"}]
        result = _merge_phones(existing, new, "merge")
        assert len(result) == 2

    def test_replace_overwrites_all(self):
        existing = [{"value": "+79270000000", "type": "mobile"}, {"value": "250", "type": "internal"}]
        new = [{"value": "+79998887766", "type": "work"}]
        result = _merge_phones(existing, new, "replace")
        assert len(result) == 1
        assert result[0]["value"] == "+79998887766"

    def test_remove_deletes_matching(self):
        existing = [
            {"value": "+79270000000", "type": "mobile"},
            {"value": "+78482123456", "type": "work"},
        ]
        remove = [{"value": "+79270000000"}]
        result = _merge_phones(existing, remove, "remove")
        assert len(result) == 1
        assert result[0]["value"] == "+78482123456"

    def test_remove_no_match_keeps_all(self):
        existing = [{"value": "+79270000000", "type": "mobile"}]
        remove = [{"value": "+70000000000"}]
        result = _merge_phones(existing, remove, "remove")
        assert len(result) == 1

    def test_merge_empty_existing(self):
        new = [{"value": "+79270000000", "type": "mobile"}]
        result = _merge_phones([], new, "merge")
        assert len(result) == 1

    def test_replace_empty_new(self):
        existing = [{"value": "+79270000000", "type": "mobile"}]
        result = _merge_phones(existing, [], "replace")
        assert result == []


# =============================================================================
# _merge_emails
# =============================================================================

class TestMergeEmails:
    def test_merge_adds_new_email(self):
        existing = [{"value": "work@example.com", "type": "work"}]
        new = [{"value": "personal@example.com", "type": "home"}]
        result = _merge_emails(existing, new, "merge")
        assert len(result) == 2

    def test_merge_deduplicates_case_insensitive(self):
        existing = [{"value": "User@Example.COM", "type": "work"}]
        new = [{"value": "user@example.com", "type": "home"}]
        result = _merge_emails(existing, new, "merge")
        assert len(result) == 1

    def test_replace(self):
        existing = [{"value": "old@example.com", "type": "work"}]
        new = [{"value": "new@example.com", "type": "home"}]
        result = _merge_emails(existing, new, "replace")
        assert len(result) == 1
        assert result[0]["value"] == "new@example.com"

    def test_remove(self):
        existing = [
            {"value": "keep@example.com", "type": "work"},
            {"value": "remove@example.com", "type": "home"},
        ]
        remove = [{"value": "remove@example.com"}]
        result = _merge_emails(existing, remove, "remove")
        assert len(result) == 1
        assert result[0]["value"] == "keep@example.com"

    def test_merge_empty_existing(self):
        new = [{"value": "new@example.com", "type": "work"}]
        result = _merge_emails([], new, "merge")
        assert len(result) == 1


# =============================================================================
# _merge_organizations
# =============================================================================

class TestMergeOrganizations:
    def test_merge_adds_new_org(self):
        existing = [{"name": "OldCorp", "title": "CTO"}]
        new = [{"name": "NewCorp", "title": "Director"}]
        result = _merge_organizations(existing, new, "merge")
        assert len(result) == 2

    def test_merge_deduplicates_by_name(self):
        existing = [{"name": "Greenline", "title": "CTO"}]
        new = [{"name": "greenline", "title": "Director"}]
        result = _merge_organizations(existing, new, "merge")
        assert len(result) == 1

    def test_replace(self):
        existing = [{"name": "OldCorp"}]
        new = [{"name": "NewCorp"}]
        result = _merge_organizations(existing, new, "replace")
        assert len(result) == 1
        assert result[0]["name"] == "NewCorp"

    def test_remove(self):
        existing = [{"name": "Keep"}, {"name": "Remove"}]
        remove = [{"name": "Remove"}]
        result = _merge_organizations(existing, remove, "remove")
        assert len(result) == 1
        assert result[0]["name"] == "Keep"

    def test_merge_empty_existing(self):
        new = [{"name": "NewCorp"}]
        result = _merge_organizations([], new, "merge")
        assert len(result) == 1


# =============================================================================
# Internal PBX type — end-to-end through build+format
# =============================================================================

class TestInternalATSType:
    def test_build_internal_phone(self):
        body = _build_person_body(
            phones=[{"number": "250", "type": "internal"}]
        )
        pn = body["phoneNumbers"][0]
        assert pn["value"] == "250"
        assert pn["type"] == "internal"
        assert "+" not in pn["value"]

    def test_format_internal_phone_single(self):
        person = {
            "resourceName": "people/c1",
            "phoneNumbers": [{"value": "250", "type": "internal"}],
        }
        result = _format_contact(person)
        assert "Phone: 250 (Internal)" in result

    def test_format_internal_phone_in_multi(self):
        person = {
            "resourceName": "people/c1",
            "phoneNumbers": [
                {"value": "+79270000000", "type": "mobile"},
                {"value": "250", "type": "internal"},
            ],
        }
        result = _format_contact(person)
        assert "  - 250 (Internal)" in result

    def test_merge_two_internal_numbers_stay_separate(self):
        """Different internal numbers (250 vs 301) both preserved."""
        existing = [{"value": "250", "type": "internal"}]
        new = [{"value": "301", "type": "internal"}]
        result = _merge_phones(existing, new, "merge")
        assert len(result) == 2

    def test_merge_same_internal_number_deduped(self):
        existing = [{"value": "250", "type": "internal"}]
        new = [{"value": "250", "type": "internal"}]
        result = _merge_phones(existing, new, "merge")
        assert len(result) == 1


# =============================================================================
# _build_person_body — batch-compatible (notes, address in new API)
# =============================================================================

class TestBuildPersonBodyBatch:
    def test_notes_included_in_batch_body(self):
        body = _build_person_body(
            given_name="Test",
            notes="Important VIP",
        )
        assert "biographies" in body
        assert body["biographies"][0]["value"] == "Important VIP"

    def test_address_included_in_batch_body(self):
        body = _build_person_body(
            given_name="Test",
            address="123 Main St, Moscow",
        )
        assert "addresses" in body
        assert body["addresses"][0]["formattedValue"] == "123 Main St, Moscow"

    def test_phones_and_notes_together(self):
        body = _build_person_body(
            phones=[{"number": "+79270000000", "type": "mobile"}],
            notes="Call after 10am",
        )
        assert "phoneNumbers" in body
        assert "biographies" in body
