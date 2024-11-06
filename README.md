# Whisper Project
=====================

**Descrizione**
---------------

Il Progetto OpenFiles è un sistema di download e trascrizione di file audio da YouTube utilizzando yt-dlp e Whisper, con l'aggiunta di una interfaccia grafica creata con Tkinter.

**Funzionalità**
-----------------

*   **Download**: il sistema scarica i file audio da YouTube utilizzando yt-dlp.
*   **Trascrizione**: dopo aver scaricato il file audio, il sistema esegue la trascrizione del contenuto del file utilizzando Whisper.
*   **Interfaccia grafica**: l'interfaccia è creata con Tkinter e consente di inserire il link del video da scaricare e di selezionare le impostazioni per la trascrizione.

**Come utilizzare**
-------------------

### Utilizzo con `main.py`

1.  Esegui il file `main.py` per avviare l'applicazione.
2.  Una finestra grafica verrà visualizzata, in cui potrai inserire il link del video YouTube da scaricare e selezionare le impostazioni desiderate per la trascrizione.
3.  Clicca sul pulsante "Avvia Download e Trascrizione" per iniziare il processo di download e trascrizione.

### Utilizzo con `main_cli.py`

1.  Esegui il file `main_cli.py` per avviare l'applicazione.
2.  Sarai richiesto di inserire alcuni dati, come ad esempio il link del video YouTube da scaricare, il nome del file da creare e le impostazioni desiderate per la trascrizione.
3.  Inserisci i dati richiesti e premi invio per iniziare il processo di download e trascrizione.

**Requisiti**
------------

*   Python 3.11 o successivo
*   yt-dlp
*   Whisper
*   Tkinter (per l'interfaccia grafica)
*   Docker 

**Nota importante**
--------------------

Il sistema utilizza un contatore Docker personalizzato, basato su rocm-terminal e modificato per includere tutte le dipendenze necessarie all'utilizzo di rocm e pytorch. Tuttavia, è attualmente possibile utilizzare il sistema con altri container Docker, dopo aver modificato alcune variabili come il nome del container e i vari path al suo interno.

**In fase di sviluppo**
---------------------

È in corso lo sviluppo di una versione che permetterà di utilizzare un file di configurazione per modificare diversi paramentri per il funzionamento senza toccare il codice principale del progetto (path delle varie directory, nome container ecc..). 
In futuro è mia intenzione implementare l'uso di questo progetto anche senza l'uso di docker, cosa che potrà essere dichiarata direttamente dal file di configurazione di cui parlavo pocanzi. 
Non essendo a disposizione di una GPU Nvidia molto probabilmente non mi sarà possibile testare la funzionalità del progetto in locale con l'accelerazione CUDA.

