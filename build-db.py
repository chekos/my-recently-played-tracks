import json
from pathlib import Path

import git
import pandas as pd
from rich.progress import track as track_progress
from rich import print


# from git-history src code
def iterate_file_versions(
    repo_path,
    filepath,
    ref="main",
):

    repo = git.Repo(repo_path, odbt=git.GitDB)

    # pull latest changes
    try:
        repo.remotes[0].pull()
    except:
        pass

    commits = reversed(list(repo.iter_commits(ref)))
    for commit in track_progress(commits, description="Processing commits..."):
        try:
            for tree in commit.tree.trees:
                for blobs in tree.blobs:
                    if filepath in blobs.name:
                        yield blobs.data_stream.read()

        except IndexError:
            # This commit doesn't have a copy of the requested file
            pass


def get_file_versions(repo_path, filename):
    full_file = [
        json.loads(file) for file in list(iterate_file_versions(repo_path, filename))
    ]
    return full_file


def build_tracks_dataframe(tracks_played):
    tracks_holder = []
    for item in track_progress(tracks_played, description="Building dataframe..."):
        current_item = {}
        current_item["played_at"] = item["played_at"]

        track = item["track"]
        album = track["album"]
        artists = track["artists"]

        # artists
        current_item["track_artists"] = " & ".join(
            [f"{artist['name']}" for artist in artists]
        )

        # track
        current_item["track_name"] = track["name"]
        current_item["track_popularity"] = track["popularity"]
        current_item["track_duration_ms"] = track["duration_ms"]
        current_item["track_explicit"] = track["explicit"]
        current_item["track_spotify_url"] = track["external_urls"]["spotify"]
        current_item["track_preview_url"] = track["preview_url"]
        current_item["track_track_number"] = track["track_number"]
        current_item["track_uri"] = track["uri"]
        current_item["track_disc_number"] = track["disc_number"]
        current_item["track_href"] = track["href"]
        current_item["track_id"] = track["id"]
        current_item["track_is_local"] = track["is_local"]
        for external_id in track["external_ids"]:
            current_item[f"track_external_ids_{external_id}"] = track["external_ids"][
                external_id
            ]
        current_item["track_artists_uris"] = " & ".join(
            [f"{artist['name']}_{artist['uri']}" for artist in artists]
        )

        # album
        current_item["album_name"] = album["name"]
        current_item["album_spotify_url"] = album["external_urls"]["spotify"]
        current_item["album_release_date"] = album["release_date"]
        current_item["album_uri"] = album["uri"]
        current_item["album_id"] = album["id"]
        current_item["album_href"] = album["href"]
        current_item["album_release_date_precision"] = album["release_date_precision"]
        current_item["album_type"] = album["album_type"]
        current_item["album_total_tracks"] = album["total_tracks"]
        for image in album["images"]:
            height = image["height"]
            width = image["width"]
            url = image["url"]
            current_item[f"album_image_{height}x{width}_url"] = url
        album_artist = album["artists"][0]
        current_item["album_artist_spotify_url"] = album_artist["external_urls"][
            "spotify"
        ]
        current_item["album_artist_href"] = album_artist["href"]
        current_item["album_artist_id"] = album_artist["id"]
        current_item["album_artist_name"] = album_artist["name"]
        current_item["album_artist_uri"] = album_artist["uri"]
        current_item["album_artists"] = " & ".join(
            artist["name"] for artist in album["artists"]
        )

        tracks_holder.append(current_item)
    return tracks_holder


def write_datasets(tracks_played, include_long=True, include_json=True):
    tracks_holder = build_tracks_dataframe(tracks_played)
    data = pd.DataFrame(tracks_holder).drop_duplicates().sort_values(by="played_at")
    print("Writing ./tracks.csv")
    data.to_csv("tracks.csv", index=False, encoding="utf-8")
    if include_long:
        print("Writing ./tracks_long.csv")
        data["artists"] = data["track_artists"].str.split(" & ")
        data = data.explode("artists")
        data.to_csv("tracks_long.csv", index=False, encoding="utf-8")
    if include_json:
        with open("tracks.json", "w") as file:
            json.dump(tracks_played, file, default=str)


def get_tracks_played():
    repo_path = Path("./spotify-git-scraping/").resolve()
    recently_played_jsons = get_file_versions(repo_path, "recently_played.json")
    tracks_played = []
    for item in track_progress(
        recently_played_jsons, description="Processing tracks_played..."
    ):
        items = item["items"]
        if len(items) > 0:
            tracks_played.extend(items)
    _unique = {item["played_at"]: item for item in tracks_played}
    tracks_played = [track for track in _unique.values()]
    return tracks_played


if __name__ == "__main__":
    tracks_played = get_tracks_played()
    write_datasets(tracks_played)
