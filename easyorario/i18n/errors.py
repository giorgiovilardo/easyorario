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
    "class_identifier_too_long": "L'identificativo della classe non può superare 255 caratteri",
    "school_year_required": "L'anno scolastico è obbligatorio",
    "weekly_hours_invalid": "Le ore settimanali devono essere un numero tra 1 e 60",
    "subjects_required": "Inserire almeno una materia",
    "teachers_format_invalid": "Formato non valido per i docenti. Usare 'Materia: Nome Docente' per ogni riga",
    "constraint_text_required": "Il testo del vincolo è obbligatorio",
    "constraint_text_too_long": "Il testo del vincolo non può superare 1000 caratteri",
    "llm_connection_failed": "Impossibile connettersi all'endpoint LLM",
    "llm_auth_failed": "Chiave API non valida",
    "llm_timeout": "Timeout durante il test di connessione",
    "llm_base_url_required": "L'URL base dell'endpoint LLM è obbligatorio",
    "llm_api_key_required": "La chiave API è obbligatoria",
    "llm_config_saved": "Configurazione LLM salvata con successo",
    "llm_config_required": "Configura l'endpoint LLM prima di procedere",
    "llm_translation_failed": "Errore durante la traduzione del vincolo",
    "llm_translation_malformed": "Il modello ha restituito una risposta non valida. Prova a riformulare il vincolo",
    "llm_translation_timeout": "Timeout durante la traduzione del vincolo",
    "translation_success": "Vincoli tradotti con successo",
    "all_translations_failed": "Impossibile tradurre i vincoli. Verifica la configurazione LLM o riformula i vincoli",
    "no_pending_constraints": "Nessun vincolo in attesa di traduzione",
    "constraint_not_translatable": "Il vincolo deve essere nello stato 'tradotto' per essere approvato o rifiutato",
    "conflict_teacher_double_booking": (
        "Conflitto: {teacher} è assegnato a più lezioni contemporaneamente ({day}, ora {slot})"
    ),
    "conflict_hour_total_mismatch": (
        "Le ore totali assegnate ({total}) superano le ore settimanali dell'orario ({weekly_hours})"
    ),
}
