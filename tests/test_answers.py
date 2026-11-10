from datetime import date

from job_agent.apply.answers import CHECK, SKIP, build_answers, pick_option

APPLICANT = {"first_name": "Ayush", "last_name": "Kshitij", "email": "a@x.com", "phone": "+91 7318367493",
             "location": "Goa, India", "linkedin": "https://www.linkedin.com/in/ayush-kshitij",
             "github": "https://github.com/AyushKshitij45", "years_experience": 2, "current_company": "Acies",
             "current_title": "Software Engineer", "work_authorized": "Yes", "needs_sponsorship": "No",
             "heard_about_us": "Company careers site", "gender": "Male", "disability": "No", "veteran": "No",
             "cover_letter": "skip", "address": ""}
SCREENING = {"notice_period_days": 45, "current_ctc_lpa": 8, "expected_ctc": {"preferred_lpa": 14}, "willing_to_relocate": True}
EDUCATION = {"school": "KIIT", "degree": "Bachelor of Technology", "discipline": "Computer Science", "end_year": 2026, "gpa": "8.11"}

answer = build_answers(APPLICANT, SCREENING, EDUCATION, today=date(2026, 11, 10))


def test_identity_and_links():
    assert answer("First Name*") == "Ayush"
    assert answer("Last Name*") == "Kshitij"
    assert answer("Email*") == "a@x.com"
    assert answer("LinkedIn Profile, Github, Personal Website, or Portfolio") == APPLICANT["linkedin"]
    assert answer("Website") == APPLICANT["github"]


def test_work_authorisation_and_screening_questions():
    assert answer("Do you have the legal right to work in the country where you are applying to work?*") == "Yes"
    assert answer("Are you currently eligible to work in India?*") == "Yes"
    assert answer("Do you, now or in the future, require a work permit, visa, or additional right to work support?*") == "No"
    assert answer("Do you require visa sponsorship, now or in the future, to continue working in India?*") == "No"
    assert answer("Do you currently work for, or have you previously worked for Zscaler?*") == "No"
    assert answer("Have you been involved in procurement or contract award activities involving Zscaler?*") == "No"
    assert answer("How did you learn about this job?*") == "Company careers site"
    assert answer("Who is your current or previous employer?*") == "Acies"
    assert answer("What is your current or previous job title?*") == "Software Engineer"
    assert answer("Notice period") == "45 days"
    assert answer("Expected CTC") == "14 LPA"
    assert answer("Current CTC") == "8 LPA"
    assert answer("Total years of experience") == "2"
    assert answer("Are you willing to relocate?") == "Yes"


def test_location_country_and_address():
    assert answer("Country*") == "India"
    assert answer("Please select the country where you currently reside. *") == "India"
    assert answer("Location (City)*") == "Goa, India"
    assert answer("In what city and state is your primary residence? (e.g. San Jose, CA)*") == "Goa, India"
    assert answer("Home Address*") is None                       # not configured -> unanswered


def test_demographics_education_and_dates():
    assert answer("Sex*") == "Male"
    assert answer("Gender") == "Male"
    assert answer("Disability Status") == "No"
    assert answer("Veteran Status") == "No"
    assert answer("Race / Ethnicity") == "Decline"
    assert answer("School*") == "KIIT"
    assert answer("Degree*") == "Bachelor of Technology"
    assert answer("Similarly, we also invite you to provide your GPA") == "8.11"
    assert answer("When are you available to start full-time? *") == "2026-12-25"


def test_skips_consents_and_unknowns():
    assert answer("Preferred Name") == SKIP
    assert answer("Pronouns") == SKIP
    assert answer("If you selected Other please tell us how you learned about this job.") == SKIP
    assert answer("Zscaler Privacy Policy *") == CHECK
    assert answer("I Agree") == CHECK
    assert answer("By checking this box, I consent to Zscaler collecting my responses") == CHECK
    assert answer("What is your favourite programming paradigm?*") is None


def test_pick_option_exact_substring_yes_no_decline_date_and_word_overlap():
    assert pick_option(["Female", "Male", "Decline To Self Identify"], "Male") == "Male"
    assert pick_option(["United States +1", "India +91"], "India") == "India +91"
    assert pick_option(["Select...", "Yes", "No"], "yes") == "Yes"
    assert pick_option(["Asian", "I don't wish to answer"], "Decline") is None     # no decline-like option
    assert pick_option(["Asian", "Decline to self-identify"], "Decline") == "Decline to self-identify"
    assert pick_option(["Q4 2026 (October - December)", "Q1 2027 (January - March)"], "2026-12-25") == "Q4 2026 (October - December)"
    assert pick_option(["LinkedIn", "Company Website", "Other"], "Company careers site") == "Company Website"
    assert pick_option(["Bachelor's Degree", "Master's Degree"], "Bachelor of Technology") == "Bachelor's Degree"
    assert pick_option(["LinkedIn", "Other"], "Company careers site") is None


def test_pick_option_yes_no_is_whole_word_only():
    options = ["Yes, I will require visa sponsorship now or in the future to continue working here.",
               "No, I will not require visa sponsorship."]
    assert pick_option(options, "No") == options[1]                # "no" inside "now" must not count
    assert pick_option(options, "Yes") == options[0]
    assert pick_option(["Nothing", "Nope"], "No") is None


def test_pick_option_prefers_an_option_starting_with_the_value():
    assert pick_option(["Old Goa, Goa, India", "Goa, India", "Goa Velha, Goa, India"], "Goa, India") == "Goa, India"


def test_answer_leaves_test_scores_alone_and_degree_needs_the_word():
    assert answer("we invite you to share your SAT or ACT score if you feel comfortable") == SKIP
    assert answer("Highest qualification") is None
