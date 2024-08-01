### Step-by-Step Procedure for Snippet & Template Development and Deployment

#### 1. **Workspace**
   - **Navigate to Workspace:**
     - Go to the **[Halerium](https://pro.halerium.ai/erium/64f567067afcd200121177aa/contents/Snippets%20Development)**, "Code Snippets & Scripts" workspace and "Snippet Development folder" .

#### 2. **Development Phase**
   - **Create a New Snippet:**
     - Inside the "Snippet Development" folder, go to the "__in_progress" subfolder.
     - Create a new board file to start building and experimenting with your snippet.

#### 3. **Testing Phase**
   - **Push to Testing:**
     - Once satisfied with the snippet, move it to the "__testing" subfolder.
   - **Feedback Collection:**
     - Send the snippet out for feedback from other users or colleagues.
     - Collect and incorporate the necessary feedback.

#### 4. **Finalization Phase**
   - **Move to Final Folder:**
     - After the feedback stage, push the snippet to the "__snippets_final" folder.
   - **Organize Snippets:**
     - Inside the "snippets_final" folder, there is another folder called "snippets."
     - Within "__snippets," there are 7 different subfolders:
       1. Essentials
       2. Communications and Administration
       3. Project Management
       4. Coding and Data
       5. Sales
       6. Document Tools
       7. Canvas
     - Choose the appropriate category for your snippet that best fits in.
    - If need to create a new folder:
        - create in the following format: 0X_Snippet_Catergory
        - inside the folder create "snippet_categories.json" file.
        - In the json fill up the following
       ```json
        {
        "name": Name of snippet catergory,
        "description": what types of snippet exist in this snippet folder
        }
        ```

#### 5. **Category and Priority Assignment**
   - **Create a Folder:**
     - Under the chosen category (e.g., Essentials), create a new folder.
     - Name the folder with a number corresponding to its priority (e.g., 01_bot_with_context).

   - **Create Documents:**
     - Inside the newly created folder, create two documents:
       1. `snippet.board` - This file contains the final snippet template exist.
       2. `snippet.json` - This file includes the name and description of the snippet.
       ```json
        {
        "name": Name of snippet,
        "description": Function of this snippet
        }
        ```
#### 6. **Tips by Guhan**
   - **[Snippets] folder:**
     - Upload the developed snippets to [Snippets] folder for quick testing.
- **[Develop] space:**
    - Also in [**Develop**](https://develop.halerium.ai/erium/6548ff5ee150aa001251645b), I have a copy of the snippets and my practice is to upload the __snippets folder into develop and download it before adding into the templates repo. Once there was a difference in version between pro and develop which affected my merge request. As a good practice I will do this extra step. 

#### 7. **Version Control and Deployment**
   - **Navigate to GitLab:**
     - Go to GitLab at https://gitlab.com/erium/templates.
   - **Create a New Branch:**
     - Branch Creation: In the repository, create a new branch to push the snippet update update. This ensures that your changes are isolated and can be reviewed before merging into the main branch. 
     - Click on the "Branches" tab.
     - Click on the "New branch" button.
     - Enter a name for your branch (e.g.,update-snippets-<sprint-cycle>).
     - Click "Create branch" (Ensure that your branch is based of `dev`).
  - **Clone the branch repository locally and work with it**
   - **Upload Snippets:**
     - Add all the snippets to this new branch under snippets folder.
   - **Testing Folder:**
     - Inside the "tests" folder, locate the `expected_snippets.py` file.
     - Add the names of the snippets you want to include to ensure the pipeline runs smoothly.
     - example:
        ```python
        expected_snippets = {
    'Essentials': [  # category name
        'Hal-E - your Halerium support bot',
        'Bot with context',
        'Board Creator',
        'Board Interpreter',  # snippet name
        'Bot Personality Generator',
        'Image Generator',
        'Questionnaire Chatbot'
    ],
    'Communication & Administration': [
        'Meeting Minutes Analyzer',
        'Fast Email Writer',
        'Advanced Email Writer',
    ]
        }
    ```

#### 8. **Merge Request and Finalization**
   - **Create a Merge Request:**
     - Once all snippets are added, create a merge request if there is no issues in the pipeline.
   - **Review and Approval:**
     - Maksim will review and update the merge request.
