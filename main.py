from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import shutil
from git import Repo
import asyncio

app = FastAPI()

class GitRepo(BaseModel):
    git_url: str
    github_token: Optional[str] = None

project_states = {}

@app.get("/")
async def get_main():
    return {"message": "Welcome to Code Reader! V6"}

@app.post("/get-repo-content/")
async def get_repo_content(repo: GitRepo):
    git_url = repo.git_url
    github_token = repo.github_token
    try:
        repo_name = git_url.split("/")[-1].replace(".git", "") if git_url.endswith(".git") else git_url.split("/")[-1]
        temp_dir = f"./temp_{repo_name}"
        if git_url not in project_states:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            repo_dir = os.path.join(temp_dir, repo_name)
            await clone_repo_async(git_url, repo_dir, github_token)
            project_states[git_url] = {"repo_dir": repo_dir, "start_index": 0, "end_of_content": False}

        state = project_states[git_url]
        if state["end_of_content"]:
            return {"content": "", "end_of_content": True}

        content, state["start_index"], state["end_of_content"] = await read_batch_files_async(state["repo_dir"], state["start_index"])
        
        if state["end_of_content"]:
            del project_states[git_url]
            shutil.rmtree(temp_dir)

        return {"content": content, "end_of_content": state["end_of_content"]}

    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=str(e))

async def clone_repo_async(git_url, repo_dir, github_token=None):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: clone_repo(git_url, repo_dir, github_token))

def clone_repo(git_url, repo_dir, github_token=None):
    if github_token:
        modified_git_url = git_url.replace('https://', f'https://{github_token}@')
    else:
        modified_git_url = git_url
    Repo.clone_from(modified_git_url, repo_dir)

async def read_batch_files_async(directory, start_index, char_limit=50000):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: read_batch_files(directory, start_index, char_limit))

def read_batch_files(directory, start_index, char_limit):
    current_chars = 0
    all_text = ""
    for root, dirs, files in os.walk(directory):
        for file_name in files:
            if current_chars >= start_index:
                file_path = os.path.join(root, file_name)
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as file:
                            file_content = file.read()
                            all_text += f"File: {file_name}\n\n{file_content}\n\n"
                            current_chars += len(file_content)
                            if current_chars - start_index >= char_limit:
                                return all_text, current_chars, False
                    except UnicodeDecodeError:
                        pass
                    except Exception as e:
                        pass
    return all_text, current_chars, True

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=80)
