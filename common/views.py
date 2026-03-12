"""Public legal information views."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET


LEGAL_OVERVIEW = {
	"privacy": "/api/legal/privacy/",
	"imprint": "/api/legal/imprint/",
}

PRIVACY_CONTENT = {
	"title": "Datenschutzerklaerung",
	"summary": "Diese Seite erklaert, welche personenbezogenen Daten bei Videoflix verarbeitet werden.",
	"sections": [
		{
			"heading": "Verantwortliche Stelle",
			"body": "Videoflix GmbH, Musterstrasse 1, 12345 Musterstadt, E-Mail: privacy@videoflix.example",
		},
		{
			"heading": "Verarbeitete Daten",
			"body": "Wir verarbeiten Registrierungsdaten, Login-Informationen und Nutzungsdaten zur Bereitstellung des Dienstes.",
		},
		{
			"heading": "Rechtsgrundlagen",
			"body": "Die Verarbeitung erfolgt zur Vertragserfuellung und auf Grundlage berechtigter Interessen gemaess DSGVO.",
		},
		{
			"heading": "Betroffenenrechte",
			"body": "Du hast das Recht auf Auskunft, Berichtigung, Loeschung, Einschraenkung und Datenuebertragbarkeit.",
		},
	],
}

IMPRINT_CONTENT = {
	"title": "Impressum",
	"summary": "Angaben gemaess gesetzlicher Informationspflichten fuer Videoflix.",
	"sections": [
		{
			"heading": "Anbieter",
			"body": "Videoflix GmbH, Musterstrasse 1, 12345 Musterstadt",
		},
		{
			"heading": "Vertreten durch",
			"body": "Max Mustermann, Geschaeftsfuehrer",
		},
		{
			"heading": "Kontakt",
			"body": "Telefon: +49 30 000000, E-Mail: info@videoflix.example",
		},
		{
			"heading": "Registereintrag",
			"body": "Handelsregister: HRB 123456, Amtsgericht Musterstadt",
		},
	],
}


@require_GET
def legal_overview(request):
	return JsonResponse(LEGAL_OVERVIEW, status=200)


@require_GET
def privacy_policy(request):
	return JsonResponse(PRIVACY_CONTENT, status=200)


@require_GET
def imprint(request):
	return JsonResponse(IMPRINT_CONTENT, status=200)
