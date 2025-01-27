function main(){
    // Get values from the input fields
    const players = document.getElementById('playersInput').value;
    const condition = document.getElementById('conditionInput').value;
    const timestamp = document.getElementById('dateSelector').value;

    console.log('players:', players);
    console.log('condition:', condition);
    console.log('timestamp:', timestamp);

    const fileInput = document.getElementById("imageInput");
    const file = fileInput.files[0];
    document.getElementById("total").innerText = ``;
    if(file) {
        //uploadImage(file)
        getLambdaRekog(file,players,condition,timestamp)
    } else {
        console.error("No file selected");
        alert("Please select and upload an image.");
        return;
    }
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
            
            let playersHTML = data.response_payload.body.round_data.players.map(player => {
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
            `;
            
            
        
        
            
        })
        .catch(error => {
            console.error("Error getting lambda rekog:", error);
            document.getElementById("total").innerText = "Error from response";
            // Hide the spinner in case of error
            spinner.style.display = 'none';
        });

}


// Function to display the success message
function showSuccessMessage() {
    // Show the overlay and message
    const overlay = document.getElementById('overlay');
    overlay.style.display = 'flex';  // Show overlay

    // Optionally hide the success message after 3 seconds
    setTimeout(() => {
        overlay.style.display = 'none'; // Hide overlay
    }, 1500);
}