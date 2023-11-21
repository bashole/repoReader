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

@app.get("/")
async def get_main():
    return {"message": "Welcome to Code Reader! V2"}

@app.post("/get-repo-content/")
async def get_repo_content(repo: GitRepo):
    git_url = repo.git_url
    github_token = repo.github_token
    try:
        repo_name = git_url.split("/")[-1].replace(".git", "") if git_url.endswith(".git") else git_url.split("/")[-1]

        temp_dir = f"./temp_{repo_name}"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        repo_dir = os.path.join(temp_dir, repo_name)
        await clone_repo_async(git_url, repo_dir, github_token)

        content = await read_all_files_async(repo_dir)
        shutil.rmtree(temp_dir)
        return {"content": content[:50000]}

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

async def read_all_files_async(directory):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: read_all_files(directory))

def read_all_files(directory):
    all_text = ""
    for root, dirs, files in os.walk(directory):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        all_text += f"File: {file_name}\n\n" + file.read() + "\n\n"
                except UnicodeDecodeError:
                    pass  # Handle file reading errors
                except Exception as e:
                    pass  # General exception handling
    return all_text

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=80)
