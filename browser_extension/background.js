// background.js
chrome.action.onClicked.addListener((tab) => {
    // Aquí el usuario configurará la URL una vez que la hospede, 
    // o podemos poner un placeholder como localhost de Streamlit por defecto.
    const url = "http://localhost:8501"; 
    
    chrome.tabs.create({ url: url });
});
