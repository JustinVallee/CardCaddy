function main(){
    const fileInput = document.getElementById("imageInput");
    const file = fileInput.files[0];
    document.getElementById("total").innerText = ``;
    if(file) {
        uploadImage(file)
        getLambdaRekog(file)
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
function getLambdaRekog(file){

    // Get the spinner element and Show the spinner
    const spinner = document.getElementById("loading-spinner");
    spinner.style.display = 'inline-block';

    // Send the request to the API REMOVED https for testing
    fetch(`https://j84muscmw3.execute-api.us-east-2.amazonaws.com/dev/jv-image-processing-bucket/${file.name}`)
        .then(response => response.json()) // Parse the JSON response
        .then(data => {
            console.log("Rekognition result:", data);

            // Directly access the 'textDetected' from the response
            const total = data.textDetected || "No text detected"; // Fallback to "No text detected" if it's empty

            // Hide the spinner once the response is processed
            spinner.style.display = 'none';
            showSuccessMessage()
            
            // Update the DOM element with the result
            document.getElementById("total").innerText = `Total Text Detected: ${total}`;
            
            
        })
        .catch(error => {
            console.error("Error getting Rekognition result:", error);
            document.getElementById("total").innerText = "Error fetching total";
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