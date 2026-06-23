# Smart Task Planner

Adaptivna web aplikacija za planiranje zadataka sa AI preporukom trajanja, analizom rizika, ponavljajućim zadacima, dnevnim planerom, statistikom i automatskim obaveštenjima unutar aplikacije.

---

## Opis

Smart Task Planner je Flask web aplikacija namenjena organizaciji, prioritizaciji i planiranju zadataka.

Za razliku od obične task manager aplikacije, ovaj sistem koristi istorijske podatke o završenim zadacima kako bi vremenom poboljšao procenu trajanja novih zadataka. Aplikacija pamti planirano i stvarno vreme rada, uči iz razlike između njih i koristi te podatke za buduće preporuke.

Projekat kombinuje upravljanje zadacima, pravila za planiranje, machine learning model, analizu rizika, dnevni planer, ponavljajuće zadatke, statistiku, analizu opterećenja i automatski notification center.

---

## Glavne funkcionalnosti

### Upravljanje zadacima

Aplikacija omogućava:

- Dodavanje novih zadataka
- Brisanje zadataka
- Završavanje zadataka
- Unos planiranog trajanja
- Unos stvarnog trajanja
- Definisanje roka
- Definisanje prioriteta
- Prikaz svih, aktivnih i završenih zadataka

---

### Sistem prioriteta

Aplikacija koristi skalu prioriteta od 1 do 5, ali korisniku prikazuje jasne nazive:

| Vrednost | Naziv |
|---|---|
| 1 | Critical |
| 2 | High |
| 3 | Normal |
| 4 | Low |
| 5 | Optional |

Na korisničkom interfejsu se ne prikazuju tehničke oznake poput P1, P2 ili P3, već čitljivi nazivi prioriteta.

---

### Smart Assistant

Prilikom dodavanja zadatka, Smart Assistant analizira podatke koje korisnik unese i prikazuje:

- Preporučeno trajanje zadatka
- Nivo pouzdanosti
- Rizik prekoračenja vremena
- Rizik kašnjenja
- Korisnički razumljiv predlog

Korisnik može klikom na dugme **Use Recommended** da primeni preporučeno trajanje.

---

### AI / Machine Learning

Aplikacija sadrži pravi machine learning deo.

Sistem čuva završene zadatke u tabeli `task_history` i koristi ih kao skup podataka za treniranje.

Model za predikciju trajanja koristi Ridge Regression i sledeće ulazne podatke:

- Planirano trajanje
- Prioritet
- Broj dana do roka
- Indikator da li je rok tokom vikenda

Ciljna vrednost modela je:

- Stvarno trajanje zadatka

Sistem koristi hibridni pristup:

- Cold-start logiku kada nema dovoljno istorijskih podataka
- Ridge Regression model kada postoji dovoljno podataka
- Ponovno treniranje nakon završenih zadataka
- AI bootstrap podatke za početnu podršku učenju

Na ovaj način aplikacija uči iz prethodnih grešaka u planiranju i vremenom poboljšava preporuke trajanja.

---

### Analiza rizika

Aplikacija procenjuje rizik zadataka na osnovu:

- Planiranog trajanja
- Preporučenog trajanja
- Blizine roka
- Prioriteta
- Trenutnog opterećenja
- Istorijskog ponašanja korisnika

Analiza rizika uključuje:

- Rizik prekoračenja vremena
- Rizik kašnjenja
- Prepoznavanje zakasnelih zadataka
- Prepoznavanje zadataka koji su za danas
- Prepoznavanje zadataka čiji se rok približava
- Prepoznavanje visokorizičnih zadataka

---

### Ponavljajući zadaci

Zadaci mogu biti podešeni da se automatski ponavljaju.

Podržani tipovi ponavljanja:

- Bez ponavljanja
- Dnevno
- Nedeljno
- Mesečno

Korisnik može podesiti i interval ponavljanja, na primer:

- Svaki 1 dan
- Svake 2 nedelje
- Svaka 3 meseca

Kada korisnik završi ponavljajući zadatak, aplikacija automatski kreira sledeći aktivni zadatak sa novim rokom.

---

### Daily Planner

Daily Planner pomaže korisniku da rasporedi aktivne zadatke u vremenske blokove.

Podržava:

- Više vremenskih blokova
- Do 10 blokova
- Automatsko raspoređivanje zadataka
- Sortiranje po prioritetu
- Sortiranje po roku
- Deljenje zadataka kroz dostupne vremenske blokove
- Prikaz zadataka koji nisu mogli da se rasporede

Planer koristi prioritet, rok i trajanje zadataka kako bi napravio realističan dnevni raspored.

---

### Statistika

Stranica sa statistikom prikazuje podatke na osnovu stvarno završenih zadataka korisnika.

Prikazuje:

- Broj završenih zadataka
- Tačnost planiranja
- Poređenje planiranog i stvarnog trajanja
- Grešku procene
- Završene zadatke po prioritetu
- Metrike produktivnosti

AI bootstrap podaci se ne koriste u korisničkoj statistici, kako veštački trening podaci ne bi pokvarili realne rezultate korisnika.

---

### Analiza opterećenja

Aplikacija analizira trenutno opterećenje korisnika na osnovu:

- Aktivnih zadataka
- Ukupnog planiranog vremena
- Hitnih zadataka
- Visokorizičnih zadataka
- Iskorišćenosti dostupnog vremena

Ovaj sistem pomaže korisniku da prepozna kada je trenutni plan previše opterećen ili rizičan.

---

### Automatska obaveštenja unutar aplikacije

Aplikacija ima automatski sistem obaveštenja koji radi unutar web stranice dok je aplikacija otvorena.

Sistem obaveštenja uključuje:

- Ikonicu/koverat za notification center
- Broj nepročitanih obaveštenja
- Toast obaveštenja
- Zvučni signal
- Čuvanje istorije obaveštenja u browser-u
- Mark read opciju
- Brisanje pojedinačnih obaveštenja
- Clear opciju
- Klik na obaveštenje označava ga kao pročitano

Automatska obaveštenja se generišu za:

- Zakasnele zadatke
- Zadatke koji su za danas
- Zadatke čiji se rok približava
- Visok rizik prekoračenja vremena
- Visok rizik kašnjenja

Sistem sprečava spam tako što isto upozorenje za isti zadatak prikazuje najviše jednom dnevno.

---

### Motivaciona obaveštenja

Notification center sadrži opciju za uključivanje ili isključivanje motivacionih obaveštenja.

Kada su uključena, aplikacija povremeno prikazuje kratke motivacione poruke dok je aplikacija otvorena.

Ova obaveštenja su opciona i korisnik ih može kontrolisati.

---

## Kako funkcioniše

### Sortiranje zadataka

Zadaci se uglavnom sortiraju prema:

1. Statusu
2. Prioritetu
3. Roku
4. Trajanju

Aktivni i važniji zadaci imaju prednost u odnosu na manje važne ili završene zadatke.

---

### Predikcija trajanja

Sistem predikcije radi u dva režima:

1. Cold-start režim  
   Koristi se kada nema dovoljno istorijskih podataka.

2. Machine learning režim  
   Koristi Ridge Regression model treniran na istoriji završenih zadataka.

Model uči iz razlike između planiranog i stvarnog trajanja zadataka.

---

### Model rizika

Model rizika kombinuje:

- Blizinu roka
- Procenu trajanja
- Prioritet
- Trenutno opterećenje
- Istorijsko ponašanje korisnika

Na osnovu toga prikazuje rizik i korisniku razumljive predloge.

---

### Logika ponavljajućih zadataka

Kada se ponavljajući zadatak završi:

1. Završeni zadatak se čuva u istoriji.
2. Trenutni zadatak dobija status završen.
3. Automatski se kreira novi zadatak.
4. Novi zadatak dobija sledeći rok na osnovu tipa i intervala ponavljanja.

---

### Logika obaveštenja

Aplikacija automatski proverava upozorenja dok je stranica otvorena.

Da ne bi došlo do previše obaveštenja:

- Isto upozorenje se prikazuje najviše jednom dnevno.
- Obaveštenja se čuvaju u notification centru.
- Pročitano/nepročitano stanje se čuva lokalno u browser-u.

---

## Tehnologije

- Python
- Flask
- SQLite
- scikit-learn
- joblib
- HTML
- CSS
- Bootstrap 5
- JavaScript
- Chart.js

---

## Instalacija

```bash
git clone https://github.com/NikolaDelibasic/smart-task-planner.git
cd smart-task-planner

python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt

python -m web.app