# Whisper Project

Questo progetto è stato creato per automatizzare il processo di download e trascrizione dei video YouTube utilizzando yt-dlp e Whisper.

## Classes.py

Il file `classes.py` contiene le classi `YTDLManager` e `Docker`, che gestiscono rispettivamente la scarica del video audio tramite yt-dlp e l'esecuzione di comandi nel contenitore Docker.

### YTDLManager:

*   Questa classe gestisce la scarica del file audio dal video YouTube utilizzando yt-dlp.
*   Contiene i metodi `verify_format`, che verifica se il formato desiderato è disponibile per il video specificato, e `download_video`, che esegue il download del file audio.

### Docker:

*   Questa classe gestisce l'esecuzione di comandi nel contenitore Docker.
*   Contiene i metodi `_find_file_by_name`, che trova un file in una directory specificata, `copy_to_container` e `copy_from_container`, che copiano rispettivamente un file dal sistema host al contenitore Docker e viceversa, e `run`, che esegue un comando nel contenitore Docker.

## Gui.py

Il file `gui.py` contiene la classe `App`, che gestisce l'interfaccia utente della finestra principale.

*   Questa classe crea una finestra con campi per inserire il link del video YouTube, il nome del file audio e la grandezza del modello Whisper da utilizzare.
*   Il bottone "Avvia Download e Trascrizione" esegue l'operazione di download e trascrizione del file audio utilizzando le classi `YTDLManager` e `Docker`.

## Test.py

Il file `test.py` contiene il codice per testare il funzionamento delle classi `YTDLManager` e `Docker`, in modo da automatizzare l'operazione di download e trascrizione dei video YouTube.

*   Il codice legge i dati di input dall'utente, crea un oggetto `YTDLManager` per scaricare il file audio, esegue lo script per riavviare i container Docker e infine copia i file nel sistema host.
