// Function to load players from the API
function loadPlayers() {
    fetch('https://vopx2v8s2d.execute-api.us-east-2.amazonaws.com/dev/cardcaddy_player?want_all_players=True')
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

function submitFormOCR(event) {
    event.preventDefault(); // Prevent the form from submitting normally (refreshes the page)

    // Get the values of playerInput and newPlayerInput
    const playerInput = document.getElementById('playerInput').value.trim();
    const newPlayerInput = document.getElementById('newPlayerInput').value.trim();

    // Validate that at least one of the fields is filled
    if (playerInput === "" && newPlayerInput === "") {
        alert("Please select at least one player.");
        return; // Stop the form from submitting
    }
   
    mainOCR(); // If validation passes, call the main function
}

function mainOCR(){
    // Get values from the input fields
    const players = addNewPlayersToSelected();
    const condition = document.getElementById('conditionInput').value;
    const timestamp = document.getElementById('dateSelector').value;

    console.log('players:', players);
    console.log('condition:', condition);
    console.log('timestamp:', timestamp);

    const fileInput = document.getElementById("imageInput");
    const file = fileInput.files[0];
    document.getElementById("digitalScorecard").innerText = ``;
    if(file) {
        uploadImage(file)
        getOcr(file,players,condition,timestamp)
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

// Function to upload the image to S3 (using async/await)
async function uploadImage(file) {
    try {
        const response = await fetch(
            `https://tmluaj55ij.execute-api.us-east-2.amazonaws.com/dev/jv-image-processing-bucket/${file.name}`,
            {
                method: 'PUT',
                headers: {
                    "Content-Type": file.type, // Automatically set the correct MIME type
                },
                body: file, // Pass the file object directly as the body
            }
        );

        if (!response.ok) {
            throw new Error(`Upload failed. Status: ${response.status}`);
        }

        console.log("Image uploaded successfully");
    } catch (error) {
        console.error("Error uploading image:", error);
    }
}

// Function to get cardCaddy-ocr result for the image
function getOcr(file,players,condition,timestamp){
    // Get the spinner element and Show the spinner
    const spinner = document.getElementById("loading-spinner");
    spinner.style.display = 'inline-block';

    // Send the request to the API REMOVED https for testing
    fetch(`https://yoq351n2v9.execute-api.us-east-2.amazonaws.com/dev/jv-image-processing-bucket/${file.name}?players=${players}&condition=${condition}&timestamp=${timestamp}`)
        .then(response => response.json()) // Parse the JSON response
        .then(data => {
            console.log("CardCaddy-ocr response:", data);

            // Hide the spinner once the response is processed
            spinner.style.display = 'none';
            showSuccessMessage()
     
            // Create the h2 to the digitalScorecard container
            const heading = document.createElement('h2');
            heading.textContent = 'Digital Scorecard';
            document.getElementById('digitalScorecard').appendChild(heading);

            // Set the innerHTML of the container to the HTML table from data.result.html_table
            document.getElementById('digitalScorecard').innerHTML += data.result.html_table;
           
            // Validate the table inputs
            validateTableInputs();

            // If the user edits a td cell, make the text color spring green
            document.querySelectorAll("td").forEach(td => {
                td.addEventListener("input", function () {
                    this.style.color = "springgreen";
                });
            });

            document.querySelectorAll("#digitalScorecard input").forEach(input => {
                input.addEventListener("input", function () {
                    const th = this.closest('tr').querySelector('th');  // Find the th in the same tr
            
                    // Check if the 'th' contains the text "PAR"
                    if (th && th.innerText.trim().toUpperCase() === "PAR") {
                        // Ensure value is a number
                        if (isNaN(this.value)) {
                            this.setCustomValidity("Enter a valid number");
                        } else if (this.value > 5 || this.value < 3) {
                            this.setCustomValidity("PAR must be 3, 4 or 5");
                        } else {
                            this.setCustomValidity(""); // Clear the custom validity message
                        }
                    } else {
                        // Ensure value is a number
                        if (isNaN(this.value)) {
                            this.setCustomValidity("Enter a valid number");
                        } else if (this.value > 15) {
                            this.setCustomValidity("Max value is 15");
                        } else if (this.value < 1) {
                            this.setCustomValidity("Min value is 1");
                        } else {
                            this.setCustomValidity(""); // Clear the custom validity message
                        }
                    }

                    // Ensure the form won't submit if invalid
                    const form = document.querySelector("form");
                    form.reportValidity(); // Triggers validation, preventing form submission if invalid
                });
            });
            

            // Removes scan button
            document.getElementById('scan-btn').style.display = 'none';

            // Adds save button
            document.getElementById("saveBtnDiv").innerHTML = '<button id="save-stats-btn" type="submit" class="btn btn-primary my-2"><i class="fa-solid fa-floppy-disk"></i> Save and Get Round Stats</button>';

            // Show Uploaded image
            const fileInput = document.getElementById('imageInput');
            const previewDiv = document.getElementById('preview');
      
            if (fileInput.files && fileInput.files[0]) {
              const reader = new FileReader();
      
              reader.onload = function (e) {
                // Create an image element and set its source
                const img = document.createElement('img');
                img.src = e.target.result;
                img.alt = "Uploaded Image";
      
                // Clear previous preview and display the new image
                previewDiv.innerHTML = '';
                previewDiv.appendChild(img);
              };
      
              // Read the selected file as a Data URL
              reader.readAsDataURL(fileInput.files[0]);
            }

        })
        .catch(error => {
            console.error("Error getting cardCaddy-ocr or Script in Fetch:", error);
            document.getElementById("digitalScorecard").innerText = `Error from response cardCaddy-ocr or Script in Fetch -- Error:${error}`;
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

// Add Todays date by default
document.addEventListener("DOMContentLoaded", function () {
    const dateInput = document.getElementById("dateSelector");
    const today = new Date();
    
    // Format to YYYY-MM-DD in local time (EST/EDT)
    const localDate = today.getFullYear() + '-' +
        String(today.getMonth() + 1).padStart(2, '0') + '-' +
        String(today.getDate()).padStart(2, '0');

    dateInput.value = localDate;
});

function validateTableInputs() {
    const inputs = document.querySelectorAll("#digitalScorecard input"); // Select all inputs in the table
    let firstInvalidInput = null; // Track the first invalid input

    inputs.forEach(input => {
        const th = input.closest('tr').querySelector('th'); // Find the corresponding <th> in the same row

        // Check if the 'th' contains the text "PAR"
        if (th && th.innerText.trim().toUpperCase() === "PAR") {
            // Validate PAR inputs (must be 3, 4, or 5)
            if (isNaN(input.value)) {
                input.setCustomValidity("Enter a valid number");
            } else if (input.value > 5 || input.value < 3) {
                input.setCustomValidity("PAR must be 3, 4, or 5");
            } else {
                input.setCustomValidity(""); // Clear the custom validity message
            }
        } else {
            // Validate score inputs (must be between 1 and 15)
            if (isNaN(input.value)) {
                input.setCustomValidity("Enter a valid number");
            } else if (input.value > 15) {
                input.setCustomValidity("Max value is 15");
            } else if (input.value < 1) {
                input.setCustomValidity("Min value is 1");
            } else {
                input.setCustomValidity(""); // Clear the custom validity message
            }
        }

        // If the input is invalid and we haven't found the first invalid input yet
        if (input.checkValidity() === false && !firstInvalidInput) {
            firstInvalidInput = input; // Track the first invalid input
        }
    });

    // Focus on the first invalid input (if any)
    if (firstInvalidInput) {
        firstInvalidInput.focus(); // Move focus to the first invalid input
        firstInvalidInput.reportValidity(); // Trigger the error message
    }

    // Return true if all inputs are valid, false otherwise
    return firstInvalidInput === null;
}

function saveForm(event){
    event.preventDefault(); // Prevent the form from submitting normally (refreshes the page)
    
    console.log('Validation if needed...')

    try {
    // Remove the style attribute from al td cells
    document.querySelectorAll("td").forEach(td => {
        td.removeAttribute("style");
    });
    // Remove the style attribute from all <th> elements
    document.querySelectorAll("th").forEach(th => {
        th.removeAttribute("style");
    });
    // Remove any <tr> containing a <td> with colspan="19"
    document.querySelectorAll("td[colspan='19']").forEach(td => {
        td.parentElement.remove(); // Remove the <tr> containing this <td>
    });
    // Call the function to process the scorecard
    const round_scores_obj = processScorecard();

    // Data to send in the POST request
    const postData = {
        round_scores_obj: round_scores_obj, 
        golf_course: document.getElementById('golfCourseInput').value,
        date: document.getElementById('dateSelector').value,
        condition: document.getElementById('conditionInput').value,
    };
    // Disable the submit button to prevent duplicate submissions
    const submitButton = document.getElementById('save-stats-btn');
    submitButton.disabled = true;
    submitButton.textContent = "Saving..."; // Update button text to indicate progress
    // cardCaddy upload-dynamodb API call
    fetch("https://dyg6cf7mje.execute-api.us-east-2.amazonaws.com/dev", {
        method: 'POST', // Specify the request method
        headers: {
            'Content-Type': 'application/json' // Set the content type to JSON
        },
        body: JSON.stringify(postData) // Convert the data to JSON format
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json(); // Parse the JSON response
    })
    .then(data => {
        console.log('Success Response from upload-dynamo:', data);

        // Remove the submit button after successful submission
        submitButton.remove();
        // Show the round stats
        showStats(data.body.round_data);

        // Create a button to refresh the page
        const refreshButton = document.createElement('button');
        refreshButton.type = 'button';
        refreshButton.className = 'btn btn-warning';
        refreshButton.textContent = 'Scan another card';
        refreshButton.addEventListener('click', () => {
            location.reload(); // Refreshes the page
        });
        document.getElementById('roundStats').appendChild(refreshButton);
        showSuccessMessage()
    })
    .catch(error => {
        console.error('Error:', error);
    });

    } catch (error) {
        console.error("An error occurred:", error.message); // Handle the error

    }
    
}

function processScorecard() {
    const table = document.querySelector('#digitalScorecard table');
    const rows = table.querySelectorAll('tr');
    const round_scores_obj = {
        hole_pars: [],
        par: 0,
        players: []
    };

    // Extract hole pars and calculate total par
    const parRow = rows[1].querySelectorAll('td input');
    parRow.forEach(input => {
        const par = parseInt(input.value, 10);
        round_scores_obj.hole_pars.push(par);
        round_scores_obj.par += par;
    });

    // Add par total to the PAR row
    const parTotalCell = document.createElement('td');
    parTotalCell.textContent = round_scores_obj.par;
    rows[1].appendChild(parTotalCell);

    // Get the playerSelect dropdown to check for player IDs
    const playerSelect = document.getElementById('playerInput');
    const playerOptions = Array.from(playerSelect.options);

    // Process each player's row
    for (let i = 2; i < rows.length; i++) {
        const playerRow = rows[i];
        const playerName = playerRow.querySelector('th').textContent.trim();
        const inputs = playerRow.querySelectorAll('td input');
        const scores = [];
        let total = 0;

        inputs.forEach(input => {
            const score = input.value ? parseInt(input.value, 10) : 0;
            scores.push(score);
            total += score;
        });

        // Calculate par averages
        const parAverages = { 3: 0, 4: 0, 5: 0 };
        const parCounts = { 3: 0, 4: 0, 5: 0 };

        scores.forEach((score, index) => {
            const par = round_scores_obj.hole_pars[index];
            if (par === 3 || par === 4 || par === 5) {
                parAverages[par] += score;
                parCounts[par]++;
            }
        });

        for (const par in parAverages) {
            if (parCounts[par] > 0) {
                parAverages[par] = (parAverages[par] / parCounts[par]).toFixed(2);
            } else {
                parAverages[par] = 0;
            }
        }

        // Check if the player name exists in the playerSelect dropdown
        const playerOption = playerOptions.find(option => option.text.toLowerCase() === playerName.toLowerCase());
        const playerId = playerOption ? playerOption.value : playerName;

        handicap = total - round_scores_obj.par

        // Add player data to round_scores_obj
        round_scores_obj.players.push({
            player_id: playerId, // Use player ID if available, otherwise use the name
            scores: scores,
            total_score: total,
            handicap: handicap,
            par_avgs: parAverages
        });

        // Add total to the end of the player's row
        const totalCell = document.createElement('td');
        totalCell.textContent = total;
        playerRow.appendChild(totalCell);
    }

    // Add total to the first row (Hole)
    const totalHeader = document.createElement('th');
    totalHeader.textContent = 'Total';
    rows[0].appendChild(totalHeader);

    console.log(round_scores_obj);
    return round_scores_obj;
}

function showStats(round_data) {
    const form = document.getElementById('inputForm');
    if (form) {
        form.remove();
    }
    const roundStatsDiv = document.getElementById('roundStats');    // Get the existing div for round stats

    const heading = document.createElement('h2');    // Add an h2 heading
    heading.textContent = 'Round Stats';
    roundStatsDiv.appendChild(heading);

     // Add a small text with golf course, date, and condition
    const detailsText = document.createElement('p');
    detailsText.textContent = `Golf Course: ${round_data.golf_course}, Date: ${round_data.date}, Condition: ${round_data.condition}`;
    detailsText.style.fontSize = '0.8em'; // Make the text smaller
    roundStatsDiv.appendChild(detailsText);

    // Create a table for the stats
    const statsTable = document.createElement('table');
    statsTable.className = 'table table-bordered table-dark table-sm'; // Add the desired classes
    const tableBody = document.createElement('tbody');

    // Create the table header
    const tableHeader = document.createElement('thead');
    const headerRow = document.createElement('tr');
    headerRow.style = '--bs-table-bg: #28a745; !important"'
    const headers = ['Player', 'Total Score', 'Handicap', 'Par&nbsp;3 Avg', 'Par&nbsp;4 Avg', 'Par&nbsp;5 Avg'];
    headers.forEach(headerText => {
        const th = document.createElement('th');
        th.innerHTML = headerText
        headerRow.appendChild(th);
    });

    tableHeader.appendChild(headerRow);
    statsTable.appendChild(tableHeader);

    // Create the table body
    round_data.players.forEach(player => {
        const row = document.createElement('tr');

        // Player Name
        const playerNameCell = document.createElement('td');
        playerNameCell.textContent = player.name;
        row.appendChild(playerNameCell);

        // Total Score
        const totalScoreCell = document.createElement('td');
        totalScoreCell.textContent = player.total_score;
        row.appendChild(totalScoreCell);

        // Handicap
        const handicapCell = document.createElement('td');
        handicapCell.textContent = player.handicap;
        row.appendChild(handicapCell);

        // Par Averages
        const par3AvgCell = document.createElement('td');
        par3AvgCell.textContent = player.par_avgs['3'];
        row.appendChild(par3AvgCell);

        const par4AvgCell = document.createElement('td');
        par4AvgCell.textContent = player.par_avgs['4'];
        row.appendChild(par4AvgCell);

        const par5AvgCell = document.createElement('td');
        par5AvgCell.textContent = player.par_avgs['5'];
        row.appendChild(par5AvgCell);

        tableBody.appendChild(row);
    });
    statsTable.appendChild(tableBody);

    // Add the table to the roundStats div
    roundStatsDiv.appendChild(statsTable);
}