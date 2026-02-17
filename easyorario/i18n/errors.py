"""Italian error and success message mappings."""

MESSAGES: dict[str, str] = {
    "email_taken": "Questo indirizzo email è già registrato",
    "password_too_short": "La password deve contenere almeno 8 caratteri",
    "password_mismatch": "Le password non corrispondono",
    "invalid_email": "Indirizzo email non valido",
    "registration_success": "Registrazione completata. Effettua l'accesso.",
    "invalid_credentials": "Email o password non validi",
    "login_required": "Effettua l'accesso per continuare",
    "logout_success": "Disconnessione effettuata",
    "forbidden": "Non hai i permessi per accedere a questa risorsa",
    "class_identifier_required": "L'identificativo della classe è obbligatorio",
    "school_year_required": "L'anno scolastico è obbligatorio",
    "weekly_hours_invalid": "Le ore settimanali devono essere un numero tra 1 e 60",
    "subjects_required": "Inserire almeno una materia",
    "teachers_format_invalid": "Formato non valido per i docenti. Usare 'Materia: Nome Docente' per ogni riga",
}
