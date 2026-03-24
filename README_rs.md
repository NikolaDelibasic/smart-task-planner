# Smart Task Planner

Adaptivni sistem za planiranje zadataka sa prediktivnim modelom, analizom rizika i dinamičkim raspoređivanjem.

---

## Opis

Smart Task Planner je web aplikacija za organizaciju i planiranje zadataka koja koristi istorijske podatke kako bi unapredila procene i optimizovala planiranje vremena.

Za razliku od klasičnih aplikacija, sistem se prilagođava korisniku i postaje precizniji kroz vreme.

---

## Funkcionalnosti

### Upravljanje zadacima
- Dodavanje, brisanje i završavanje zadataka
- Definisanje prioriteta, roka i trajanja
- Praćenje stvarnog vremena rada
- Automatsko sortiranje (aktivni prvo, završeni ispod)

---

### AI memorija
- Čuva završene zadatke u `task_history`
- Podaci ostaju i nakon brisanja taska
- Pamti:
  - planirano vs stvarno vreme
  - rokove
  - vreme završetka

---

### Predikcija trajanja
- Koristi:
  - istorijske podatke (ridge regresija)
  - heuristike (cold start)
- Daje:
  - preporučeno trajanje
  - nivo pouzdanosti
  - MAE (prosečna greška)

---

### Analiza rizika
- Detektuje:
  - rizik prekoračenja vremena
  - rizik kašnjenja
- Na osnovu:
  - istorije korisnika
  - opterećenja
  - rokova
- Prepoznaje nerealne zadatke

---

### Daily planner
- Automatsko planiranje dana
- Podržava:
  - više vremenskih blokova
  - pauze između zadataka
- Omogućava:
  - deljenje velikih zadataka

---

### Statistika
- Bazirana na istoriji
- Metike:
  - tačnost planiranja
  - produktivnost
  - greške u proceni
- Daje uvide u ponašanje korisnika

---

## Kako funkcioniše

### Prioritizacija zadataka
1. Prioritet (opadajuće)
2. Rok (najbliži prvi)
3. Trajanje (kraći prvi)

---

### Model predikcije
Koristi ridge regresiju sa parametrima:
- planirano trajanje
- prioritet
- udaljenost od roka
- vikend indikator

Fallback: heuristički model

---

### Model rizika
Kombinuje:
- istoriju korisnika
- opterećenje
- dostupno vreme

---

### Planer
- popunjava dostupne vremenske blokove
- deli velike zadatke
- poštuje pauze

---

## Tehnologije

- Python (Flask)
- SQLite
- HTML / CSS (Bootstrap)
- Chart.js

---

## Instalacija

```bash
git clone https://github.com/NikolaDelibasic/smart-task-planner.git
cd smart-task-planner

python -m venv venv
source venv/bin/activate

pip install flask

python -m web.app