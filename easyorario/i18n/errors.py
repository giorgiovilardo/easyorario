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
}
