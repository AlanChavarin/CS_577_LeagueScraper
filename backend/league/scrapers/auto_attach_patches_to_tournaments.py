"""
Script to automatically attach the correct patch to tournaments based on their dates.

For each tournament, finds the latest patch that is on or before the tournament's last_game_date.
"""
import logging

from ..models import Tournament, Patch

logger = logging.getLogger(__name__)


def attach_patches_to_tournaments():
    """
    Attach the correct patch to each tournament based on the tournament's date.
    
    For each tournament with a last_game_date, finds the latest patch where
    patch.date <= tournament.last_game_date and assigns it to the tournament.
    Changes are saved to the database.
    
    Returns:
        dict: Statistics about the operation (updated_count, no_patch_found_count, etc.)
    """
    tournaments = Tournament.objects.filter(last_game_date__isnull=False).select_related('patch')
    total_tournaments = tournaments.count()
    
    updated_count = 0
    no_patch_found_count = 0
    already_correct_count = 0
    
    print(f"\n{'='*80}")
    print(f"Starting patch attachment for {total_tournaments} tournaments")
    print(f"{'='*80}\n")
    logger.info(f"Starting patch attachment for {total_tournaments} tournaments")
    
    for tournament in tournaments:
        tournament_date = tournament.last_game_date
        current_patch = tournament.patch.version_num if tournament.patch else "None"
        
        # Find the latest patch that is on or before the tournament date
        # Order by date descending, then by version_num descending to get the latest
        matching_patch = Patch.objects.filter(
            date__lte=tournament_date
        ).order_by('-date', '-version_num').first()
        
        if not matching_patch:
            reason = f"SKIPPED: No patch found on or before tournament date ({tournament_date})"
            print(f"Tournament '{tournament.name}' (date: {tournament_date}, current patch: {current_patch}) - {reason}")
            logger.warning(
                f"Tournament '{tournament.name}' (date: {tournament_date}) - "
                f"No patch found on or before this date"
            )
            no_patch_found_count += 1
            continue
        
        # Check if the patch is already correctly assigned
        if tournament.patch == matching_patch:
            reason = f"SKIPPED: Already has correct patch ({matching_patch.version_num}, date: {matching_patch.date})"
            print(f"Tournament '{tournament.name}' (date: {tournament_date}, current patch: {current_patch}) - {reason}")
            logger.debug(
                f"Tournament '{tournament.name}' (date: {tournament_date}) - "
                f"Already has correct patch: {matching_patch.version_num}"
            )
            already_correct_count += 1
            continue
        
        # Update the tournament with the matching patch
        old_patch = tournament.patch.version_num if tournament.patch else "None"
        
        logger.info(
            f"Tournament '{tournament.name}' (date: {tournament_date}) - "
            f"Updating patch from {old_patch} to {matching_patch.version_num} "
            f"(patch date: {matching_patch.date})"
        )
        tournament.patch = matching_patch
        tournament.save(update_fields=['patch'])
        updated_count += 1
        print(f"Tournament '{tournament.name}' (date: {tournament_date}) - UPDATED: patch from {old_patch} to {matching_patch.version_num} (patch date: {matching_patch.date})")
    
    stats = {
        'total_tournaments': total_tournaments,
        'updated_count': updated_count,
        'no_patch_found_count': no_patch_found_count,
        'already_correct_count': already_correct_count,
    }
    
    logger.info(
        f"Patch attachment complete. "
        f"Updated: {updated_count}, "
        f"No patch found: {no_patch_found_count}, "
        f"Already correct: {already_correct_count}"
    )
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY:")
    print(f"  Total tournaments processed: {total_tournaments}")
    print(f"  Updated: {updated_count}")
    print(f"  No patch found: {no_patch_found_count}")
    print(f"  Already correct: {already_correct_count}")
    print("="*80 + "\n")
    
    return stats


if __name__ == '__main__':
    # Allow running as a script
    import os
    import django
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    # Run and save to database
    stats = attach_patches_to_tournaments()
    print(f"\nResults: {stats}")

