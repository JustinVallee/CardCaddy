// Function to load players from the API
function loadPlayers() {
    fetch('https://vopx2v8s2d.execute-api.us-east-2.amazonaws.com/dev/cardcaddy_player?all_players=True')
        .then(response => response.json())
        .then(data => {
            const playerSelect = document.getElementById('playerInput');
            for (const playerId in data) {
                const option = document.createElement('option');
                option.value = playerId;
                option.text = data[playerId];
                playerSelect.appendChild(option);
            }

            // Initialize the Chosen plugin after options are populated
            $(".chosen-select").chosen();
            
        })
        .catch(error => {
            console.error('Error fetching player data:', error);
        });
}

// Load players on page load
window.onload = loadPlayers;

function submitForm(event) {
    event.preventDefault(); // Prevent the form from submitting normally (refreshes the page)

    // Get the values of playerInput and newPlayerInput
    const playerInput = document.getElementById('playerInput').value.trim();
    const newPlayerInput = document.getElementById('newPlayerInput').value.trim();

    // Validate that at least one of the fields is filled
    if (playerInput === "" && newPlayerInput === "") {
        alert("Please provide at least one player (either select from the list or enter a new player).");
        return; // Stop the form from submitting
    }
   
    main(); // If validation passes, call the main function
}

function main(){
    // Get values from the input fields
    
    const players = addNewPlayersToSelected();
    const condition = document.getElementById('conditionInput').value;
    const timestamp = document.getElementById('dateSelector').value;

    console.log('players:', players);
    console.log('condition:', condition);
    console.log('timestamp:', timestamp);

    const fileInput = document.getElementById("imageInput");
    const file = fileInput.files[0];
    document.getElementById("total").innerText = ``;
    if(file) {
        uploadImage(file)
        getLambdaRekog(file,players,condition,timestamp)
    } else {
        console.error("No file selected");
        alert("Please select and upload an image.");
        return;
    }
}
// Function to get the selected players in the option
function getSelectedPlayers() {
    const playerSelect = document.getElementById('playerInput');
    const selectedOptions = Array.from(playerSelect.selectedOptions);
    const selectedPlayers = selectedOptions.map(option => option.value).join(',');
    return selectedPlayers
}

function addNewPlayersToSelected() {
    let selectPlayers = getSelectedPlayers(); // Get selected players (CSV string)
    let newPlayers = document.getElementById('newPlayerInput').value; // Get new player input

    newPlayers = newPlayers
        .replace(/\s*,\s*/g, ',') // Remove spaces around commas
        .replace(/\s+/g, ',')     // Replace spaces with commas
        .trim();                  // Trim leading/trailing spaces

    let newPlayersArray = newPlayers.split(',').filter(player => player !== ''); // Split and remove empty values
    let allPlayers;
    if (selectPlayers !== null && selectPlayers !== "") {
        // If selectPlayers has a value, split it into an array and concatenate newPlayersArray
        allPlayers = selectPlayers.split(',').concat(newPlayersArray).join(',');
    } else {
        // If selectPlayers is null or empty, just use newPlayersArray
        allPlayers = newPlayersArray.join(',');  // Convert array to CSV string
    }

    return allPlayers; // Return the final CSV string
}

// Function to upload the image to S3
function uploadImage(file){

   fetch(`https://tmluaj55ij.execute-api.us-east-2.amazonaws.com/dev/jv-image-processing-bucket/${file.name}`, {
        method: 'PUT',
        headers: {
            "Content-Type": file.type // Automatically set the correct MIME type
        },
        body: file // Pass the file object directly as the body
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Upload failed. Status: ${response.status}`);
        }
        console.log("Image uploaded successfully");
    })
    .catch(error => {
        console.error("Error uploading image:", error);
    });
}

// Function to get Lambda Rekognition result for the image
function getLambdaRekog(file,players,condition,timestamp){

    // Get the spinner element and Show the spinner
    const spinner = document.getElementById("loading-spinner");
    spinner.style.display = 'inline-block';

    // Send the request to the API REMOVED https for testing
    fetch(`https://j84muscmw3.execute-api.us-east-2.amazonaws.com/dev/jv-image-processing-bucket/${file.name}?players=${players}&condition=${condition}&timestamp=${timestamp}`)
        .then(response => response.json()) // Parse the JSON response
        .then(data => {
            console.log("Lambda Rekog(ocr) response:", data);

            // Directly access the 'textDetected' from the response
            //const total = data.textDetected || "No text detected"; // Fallback to "No text detected" if it's empty

            // Hide the spinner once the response is processed
            spinner.style.display = 'none';
            showSuccessMessage()
            
            /*let playersHTML = data.response_payload.body.round_data.players.map(player => {
                return `
                    <p><strong>Player ID:</strong> ${player.player_id}</p>
                    <p><strong>Name:</strong> ${player.name}</p>
                    <p><strong>Total Score:</strong> ${player.total_score}</p>
                    <p><strong>Handicap:</strong> ${player.handicap}</p>
                    <p><strong>Par Averages:</strong> ${JSON.stringify(player.par_avgs, null, 2)}</p>
                    <p><strong>Scores:</strong> ${player.scores.join(', ')}</p> <!-- Display individual scores -->
                    <hr> <!-- Adding a separator between players -->
                `;
            }).join(''); // Join all player entries into a single string
            
            document.getElementById("total").innerHTML = `
                <h4>Response Summary</h4>
                <p><strong>Message:</strong> ${data.response_payload.body.message}</p>
                
                <h5>Players</h5>
                ${playersHTML}
                
                <p><strong>Round ID:</strong> ${data.response_payload.body.round_data.round_id}</p>
                <p><strong>Condition:</strong> ${data.response_payload.body.round_data.condition}</p>
                <p><strong>Timestamp:</strong> ${data.response_payload.body.round_data.timestamp}</p>
            `;*/
            let htmlContent = "<h4>Response Summary</h4>";
            data.forEach(item => {
                htmlContent += `<p>
                    <strong>Detected Text:</strong> ${item.DetectedText} <br>
                    <strong>Confidence:</strong> ${item.Confidence.toFixed(2)}% <br>
                    <strong>Id:</strong> ${item.Id} <br>
                    ${item.ParentId ? `<strong>Parent Id:</strong> ${item.ParentId} <br>` : ""}
                </p>`;
            });
            document.getElementById("total").innerHTML = htmlContent;
            
        

        })
        .catch(error => {
            console.error("Error getting lambda rekog:", error);
            document.getElementById("total").innerText = "Error from response lambda rekog";
            // Hide the spinner in case of error
            spinner.style.display = 'none';
        });

}

// Function to display the success message
function showSuccessMessage() {
    // Show the overlay and message
    const overlay = document.getElementById('overlay');
    overlay.style.display = 'flex';  // Show overlay

    // Hide the success message after 0.8 seconds
    setTimeout(() => {
        overlay.style.display = 'none'; // Hide overlay
    }, 800);
}